#version 330 core

/*
 * CustomSkyLayerPORT.glsl
 *
 * Numeric/rendering-stage port of:
 *   full-files/src/minecraft/net/minecraft/src/CustomSkyLayer.java
 *
 * This is one source file for two OpenGL shader stages. Compile it twice:
 *   - vertex stage: define CUSTOM_SKY_LAYER_VERTEX
 *   - fragment stage: define CUSTOM_SKY_LAYER_FRAGMENT
 * If neither symbol is defined, the fragment stage is selected.
 *
 * Draw the vertex stage with:
 *   glDrawArrays(GL_TRIANGLES, 0, 36)
 *
 * The Java source submits six GL_QUADS. The 36 generated vertices below are
 * the equivalent six quads represented as two triangles each. The source
 * positions, atlas coordinates, face order, rotations, weather weighting,
 * fade intervals, validation arithmetic, and render threshold are retained.
 *
 * GLSL-covered behavior from CustomSkyLayer.java:
 *   - normalizeTime(), timeBetween(), and numeric fade-brightness math;
 *   - numeric isValid() checks and derived startFadeOut;
 *   - clear/rain/thunder weighting and Config.limit()-equivalent clamping;
 *   - isActive() time gating and day-mask membership;
 *   - the six renderSide() quads, exact atlas UVs, and all matrix rotations;
 *   - texture sampling, brightness modulation, and the f3 < 1.0E-4 skip.
 *
 * Host-side responsibilities that GLSL cannot perform by itself:
 *   - construct/read Properties and parse strings or emit Config.warn();
 *   - resolve source with TextureUtils and load/verify the texture resource;
 *   - query World.getWorldTime(), celestial/weather values, and dimension data;
 *   - upload the parsed values/day mask and bind the texture sampler;
 *   - issue the draw call and provide the pre-existing model-view matrix;
 *   - perform push/pop matrix-stack operations and configure GL blending;
 *   - expose Java boolean returns, textureId/source fields, or toString().
 *
 * The shader therefore contains all behavior that is a pure numeric or
 * rendering-stage operation, while Java remains the resource/configuration
 * and OpenGL-command boundary. uLayerValid is the host-side resource result;
 * the shader independently repeats the numeric isValid() portion below.
 *
 * The uniforms below are the already-parsed values stored by CustomSkyLayer,
 * plus the render-call values supplied by CustomSky.renderSky().
 */

#if defined(CUSTOM_SKY_LAYER_VERTEX) && defined(CUSTOM_SKY_LAYER_FRAGMENT)
#error "Define only one CustomSkyLayerPORT shader stage"
#endif

#if !defined(CUSTOM_SKY_LAYER_VERTEX) && !defined(CUSTOM_SKY_LAYER_FRAGMENT)
#define CUSTOM_SKY_LAYER_FRAGMENT
#endif

const int CUSTOM_SKY_DAY_LENGTH = 24000;
const float CUSTOM_SKY_RENDER_EPSILON = 0.0001;

// Result of CustomSkyLayer.isValid() plus successful texture lookup.
uniform bool uLayerValid;

// CustomSkyLayer.render(renderTime, celestialAngle, rain, thunder).
uniform int uTimeOfDay;
uniform float uCelestialAngle;
uniform float uRainStrength;
uniform float uThunderStrength;

// CustomSkyLayer's parsed/normalized fade times.
uniform int uStartFadeIn;
uniform int uEndFadeIn;
uniform int uStartFadeOut;
uniform int uEndFadeOut;

// Blender.parseBlend(property). This is consumed by the host OpenGL state
// setup; GLSL cannot call glBlendFunc/glEnable from a shader.
uniform int uBlendMode;

// CustomSkyLayer's stored rotation state. uAxis is this.axis after Java's
// parseAxis(), not the raw property text. The Java default is (1, 0, 0).
uniform bool uRotate;
uniform float uSpeed;
uniform vec3 uAxis;

// CustomSkyLayer's parsed weather list.
uniform bool uWeatherClear;
uniform bool uWeatherRain;
uniform bool uWeatherThunder;

// If the Java days property was absent, set uDaysPresent to false. If it was
// present, uDayMask must contain one unsigned 0/1 texel per cycle slot and
// uDayCycleIndex must equal Java's computed l value in isActive().
uniform bool uDaysPresent;
uniform int uDaysLoop;
uniform int uDayCycleIndex;
uniform usamplerBuffer uDayMask;

int normalizeTime(int value)
{
    int result = value % CUSTOM_SKY_DAY_LENGTH;
    return result < 0 ? result + CUSTOM_SKY_DAY_LENGTH : result;
}

bool timeBetween(int time, int start, int end)
{
    if (start <= end)
    {
        return time >= start && time <= end;
    }

    return time >= start || time <= end;
}

int effectiveStartFadeOut()
{
    // isValid() stores this value in Java when startFadeOut is omitted. A
    // shader cannot mutate a Java field, so it derives the same value for the
    // current invocation.
    if (uStartFadeOut >= 0)
    {
        return uStartFadeOut;
    }

    int fadeInLength = normalizeTime(uEndFadeIn - uStartFadeIn);
    int candidate = normalizeTime(uEndFadeOut - fadeInLength);

    if (timeBetween(candidate, uStartFadeIn, uEndFadeIn))
    {
        return uEndFadeIn;
    }

    return candidate;
}

bool numericLayerIsValid()
{
    // This is the numeric part of CustomSkyLayer.isValid(). Source existence,
    // resource-path fixing, warnings, and texture lookup remain host work.
    if (uStartFadeIn < 0 || uEndFadeIn < 0 || uEndFadeOut < 0)
    {
        return false;
    }

    int startFadeOut = effectiveStartFadeOut();
    int fadeInLength = normalizeTime(uEndFadeIn - uStartFadeIn);
    int clearLength = normalizeTime(startFadeOut - uEndFadeIn);
    int fadeOutLength = normalizeTime(uEndFadeOut - startFadeOut);
    int offLength = normalizeTime(uStartFadeIn - uEndFadeOut);
    int totalLength = fadeInLength + clearLength + fadeOutLength + offLength;

    if (totalLength != CUSTOM_SKY_DAY_LENGTH)
    {
        return false;
    }

    if (uSpeed < 0.0)
    {
        return false;
    }

    return uDaysLoop > 0;
}

float getFadeBrightness(int time)
{
    int startFadeOut = effectiveStartFadeOut();

    if (timeBetween(time, uStartFadeIn, uEndFadeIn))
    {
        int duration = normalizeTime(uEndFadeIn - uStartFadeIn);
        int elapsed = normalizeTime(time - uStartFadeIn);
        return float(elapsed) / float(duration);
    }
    else if (timeBetween(time, uEndFadeIn, startFadeOut))
    {
        return 1.0;
    }
    else if (timeBetween(time, startFadeOut, uEndFadeOut))
    {
        int duration = normalizeTime(uEndFadeOut - startFadeOut);
        int elapsed = normalizeTime(time - startFadeOut);
        return 1.0 - float(elapsed) / float(duration);
    }

    return 0.0;
}

float getWeatherWeight()
{
    // This is the exact f/f1/f2 accumulation from CustomSkyLayer.render().
    float clearWeight = 1.0 - uRainStrength;
    float rainWeight = uRainStrength - uThunderStrength;
    float thunderWeight = uThunderStrength;
    float weatherWeight = 0.0;

    if (uWeatherClear)
    {
        weatherWeight += clearWeight;
    }

    if (uWeatherRain)
    {
        weatherWeight += rainWeight;
    }

    if (uWeatherThunder)
    {
        weatherWeight += thunderWeight;
    }

    return clamp(weatherWeight, 0.0, 1.0);
}

bool isDayAllowed()
{
    if (!uDaysPresent)
    {
        return true;
    }

    if (uDaysLoop <= 0)
    {
        return false;
    }

    int day = uDayCycleIndex % uDaysLoop;

    if (day < 0)
    {
        day += uDaysLoop;
    }

    return texelFetch(uDayMask, day).r != 0u;
}

bool isActive()
{
    // This is the first branch of CustomSkyLayer.isActive(). The World-long
    // arithmetic is done by the host and supplied as uDayCycleIndex because
    // GLSL 330 has no portable Java-long equivalent.
    if (timeBetween(uTimeOfDay, uEndFadeOut, uStartFadeIn))
    {
        return false;
    }

    return isDayAllowed();
}

float getLayerBrightness()
{
    float brightness = getWeatherWeight() * getFadeBrightness(uTimeOfDay);
    return clamp(brightness, 0.0, 1.0);
}

#ifdef CUSTOM_SKY_LAYER_VERTEX

// Matrix state in effect before CustomSkyLayer.render() pushed and rotated
// the legacy model-view matrix.
uniform mat4 uProjection;
uniform mat4 uBaseModelView;

out vec2 vSkyTexCoord;

mat4 rotationAxisDegrees(vec3 axis, float degrees)
{
    // OpenGL's glRotatef normalizes the axis internally.
    // Java's parseAxis() rejects a zero axis and falls back to DEFAULT_AXIS.
    vec3 a = axis;

    if (dot(a, a) < 1.0e-5 || any(greaterThan(abs(a), vec3(1.0))))
    {
        a = vec3(1.0, 0.0, 0.0);
    }

    a = normalize(a);
    float angle = radians(degrees);
    float s = sin(angle);
    float c = cos(angle);
    float t = 1.0 - c;

    // mat4 constructors receive columns, matching OpenGL column-vector math.
    return mat4(
        vec4(t * a.x * a.x + c,
             t * a.x * a.y + s * a.z,
             t * a.x * a.z - s * a.y,
             0.0),
        vec4(t * a.x * a.y - s * a.z,
             t * a.y * a.y + c,
             t * a.y * a.z + s * a.x,
             0.0),
        vec4(t * a.x * a.z + s * a.y,
             t * a.y * a.z - s * a.x,
             t * a.z * a.z + c,
             0.0),
        vec4(0.0, 0.0, 0.0, 1.0));
}

vec3 skyQuadPosition(int corner)
{
    if (corner == 0)
    {
        return vec3(-100.0, -100.0, -100.0);
    }
    else if (corner == 1)
    {
        return vec3(-100.0, -100.0, 100.0);
    }
    else if (corner == 2)
    {
        return vec3(100.0, -100.0, 100.0);
    }

    return vec3(100.0, -100.0, -100.0);
}

vec2 skyAtlasCoordinate(int face, int corner)
{
    float u0 = float(face % 3) / 3.0;
    float v0 = float(face / 3) / 2.0;

    if (corner == 1 || corner == 2)
    {
        v0 += 0.5;
    }

    if (corner == 2 || corner == 3)
    {
        u0 += 1.0 / 3.0;
    }

    return vec2(u0, v0);
}

int renderFaceForQuad(int quad)
{
    // Exact renderSide() call order: 4, 1, 0, 5, 2, 3.
    if (quad == 0)
    {
        return 4;
    }
    else if (quad == 1)
    {
        return 1;
    }
    else if (quad == 2)
    {
        return 0;
    }
    else if (quad == 3)
    {
        return 5;
    }
    else if (quad == 4)
    {
        return 2;
    }

    return 3;
}

int triangleCorner(int triangleVertex)
{
    if (triangleVertex == 0 || triangleVertex == 3)
    {
        return 0;
    }
    else if (triangleVertex == 1)
    {
        return 1;
    }
    else if (triangleVertex == 2 || triangleVertex == 4)
    {
        return 2;
    }

    return 3;
}

mat4 faceMatrix(int face)
{
    mat4 matrix = mat4(1.0);

    if (uRotate)
    {
        matrix = matrix * rotationAxisDegrees(
            uAxis, uCelestialAngle * 360.0 * uSpeed);
    }

    // The first rotation is outside all six renderSide() calls.
    matrix = matrix * rotationAxisDegrees(vec3(1.0, 0.0, 0.0), 90.0);

    // Java applies this -90 degree Z rotation before renderSide(4).
    matrix = matrix * rotationAxisDegrees(vec3(0.0, 0.0, 1.0), -90.0);

    // These branches reproduce the push/pop blocks and the three successive
    // Z rotations in CustomSkyLayer.render().
    if (face == 1)
    {
        matrix = matrix * rotationAxisDegrees(vec3(1.0, 0.0, 0.0), 90.0);
    }
    else if (face == 0)
    {
        matrix = matrix * rotationAxisDegrees(vec3(1.0, 0.0, 0.0), -90.0);
    }
    else if (face == 5)
    {
        matrix = matrix * rotationAxisDegrees(vec3(0.0, 0.0, 1.0), 90.0);
    }
    else if (face == 2)
    {
        matrix = matrix * rotationAxisDegrees(vec3(0.0, 0.0, 1.0), 90.0);
        matrix = matrix * rotationAxisDegrees(vec3(0.0, 0.0, 1.0), 90.0);
    }
    else if (face == 3)
    {
        matrix = matrix * rotationAxisDegrees(vec3(0.0, 0.0, 1.0), 90.0);
        matrix = matrix * rotationAxisDegrees(vec3(0.0, 0.0, 1.0), 90.0);
        matrix = matrix * rotationAxisDegrees(vec3(0.0, 0.0, 1.0), 90.0);
    }

    return matrix;
}

void main()
{
    int quad = gl_VertexID / 6;
    int triangleVertex = gl_VertexID % 6;
    int face = renderFaceForQuad(quad);
    int corner = triangleCorner(triangleVertex);

    vSkyTexCoord = skyAtlasCoordinate(face, corner);
    gl_Position = uProjection
        * uBaseModelView
        * faceMatrix(face)
        * vec4(skyQuadPosition(corner), 1.0);
}

#endif

#ifdef CUSTOM_SKY_LAYER_FRAGMENT

uniform sampler2D uSkyAtlas;

in vec2 vSkyTexCoord;
layout(location = 0) out vec4 fragColor;

void main()
{
    // Java skips the draw when inactive or when f3 < 1.0E-4. A fragment
    // discard is the shader-stage equivalent when the host always draws the
    // fixed 36-vertex geometry.
    if (!uLayerValid || !numericLayerIsValid() || !isActive())
    {
        discard;
    }

    float brightness = getLayerBrightness();

    // !(x >= epsilon) also rejects NaN, matching Java's failed >= test.
    if (!(brightness >= CUSTOM_SKY_RENDER_EPSILON))
    {
        discard;
    }

    vec4 texel = texture(uSkyAtlas, vSkyTexCoord);

    // The legacy path modulates the bound texture by (1, 1, 1, f3). The
    // host must apply the GL blend function selected by uBlendMode.
    fragColor = texel * vec4(1.0, 1.0, 1.0, brightness);
}

#endif
