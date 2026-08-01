package dev.apacheone.exp2012.render;

import javax.imageio.ImageIO;
import java.awt.AlphaComposite;
import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Font;
import java.awt.GradientPaint;
import java.awt.Graphics2D;
import java.awt.RadialGradientPaint;
import java.awt.RenderingHints;
import java.awt.TexturePaint;
import java.awt.geom.AffineTransform;
import java.awt.geom.Ellipse2D;
import java.awt.geom.Rectangle2D;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public final class CpuSkyRenderer {
    private static final int WIDTH = 1280;
    private static final int HEIGHT = 720;
    private static final List<Star> STARS = generateStars();

    private final BufferedImage clouds;
    private final BufferedImage sun;
    private final BufferedImage moonPhases;
    private final BufferedImage rain;
    private final BufferedImage endSky;

    public CpuSkyRenderer() throws IOException {
        clouds = load("assets/minecraft/textures/environment/clouds.png");
        sun = removeDarkBackground(load("assets/minecraft/textures/environment/sun.png"));
        moonPhases = removeDarkBackground(load("assets/minecraft/textures/environment/moon_phases.png"));
        rain = load("assets/minecraft/textures/environment/rain.png");
        endSky = load("assets/minecraft/textures/environment/end_sky.png");
    }

    public List<Path> renderAll(Path outputDirectory) throws IOException {
        Files.createDirectories(outputDirectory);
        List<Path> outputs = new ArrayList<Path>();
        outputs.add(write(renderOverworld(6000L, 0.0f, "Overworld — clear day"), outputDirectory.resolve("overworld_day.png")));
        outputs.add(write(renderOverworld(12000L, 0.0f, "Overworld — sunset"), outputDirectory.resolve("overworld_sunset.png")));
        outputs.add(write(renderOverworld(18000L, 0.0f, "Overworld — moon and seeded stars"), outputDirectory.resolve("overworld_night.png")));
        outputs.add(write(renderOverworld(7000L, 0.82f, "Overworld — rain and cloud layer"), outputDirectory.resolve("overworld_rain.png")));
        outputs.add(write(renderEnd("The End — six-face sky texture study"), outputDirectory.resolve("end_skybox.png")));
        outputs.add(write(contactSheet(outputs), outputDirectory.resolve("contact_sheet.png")));
        return outputs;
    }

    private BufferedImage renderOverworld(long worldTime, float rainStrength, String label) {
        BufferedImage image = new BufferedImage(WIDTH, HEIGHT, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = image.createGraphics();
        configure(g);

        float angle = calculateCelestialAngle(worldTime, 0.0f);
        float day = clamp((float)Math.cos(angle * Math.PI * 2.0) * 2.0f + 0.5f, 0.0f, 1.0f);
        Color fog = fogColor(angle);
        Color zenithDay = new Color(82, 145, 228);
        Color zenithNight = new Color(3, 7, 24);
        Color horizonNight = new Color(12, 18, 38);
        Color zenith = blend(zenithNight, zenithDay, day);
        Color horizon = blend(horizonNight, fog, day);
        if (rainStrength > 0.0f) {
            zenith = blend(zenith, new Color(56, 65, 78), rainStrength * 0.72f);
            horizon = blend(horizon, new Color(83, 91, 101), rainStrength * 0.68f);
        }
        g.setPaint(new GradientPaint(0, 0, zenith, 0, HEIGHT, horizon));
        g.fillRect(0, 0, WIDTH, HEIGHT);

        drawSunrise(g, angle);
        drawStars(g, angle, 1.0f - day);
        drawCelestialBodies(g, angle, worldTime, day);
        drawClouds(g, worldTime, day, rainStrength);
        if (rainStrength > 0.0f) {
            drawRain(g, worldTime, rainStrength);
        }
        drawGroundSilhouette(g, day, rainStrength);
        drawLabel(g, label, worldTime, angle);
        g.dispose();
        return image;
    }

    private BufferedImage renderEnd(String label) {
        BufferedImage image = new BufferedImage(WIDTH, HEIGHT, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = image.createGraphics();
        configure(g);
        g.setColor(new Color(7, 4, 12));
        g.fillRect(0, 0, WIDTH, HEIGHT);

        int face = 310;
        int gap = 14;
        int total = face * 3 + gap * 2;
        int startX = (WIDTH - total) / 2;
        int startY = 44;
        for (int i = 0; i < 6; i++) {
            int column = i % 3;
            int row = i / 3;
            int x = startX + column * (face + gap);
            int y = startY + row * (face - 10);
            BufferedImage tile = tint(scale(endSky, face, face), new Color(40, 40, 40), 0.78f);
            AffineTransform old = g.getTransform();
            g.translate(x + face / 2.0, y + face / 2.0);
            g.rotate((i - 2) * 0.035);
            g.drawImage(tile, -face / 2, -face / 2, null);
            g.setTransform(old);
            g.setColor(new Color(150, 126, 173, 150));
            g.setStroke(new BasicStroke(2.0f));
            g.drawRect(x, y, face, face);
        }
        drawLabel(g, label, 0L, 0.0f);
        g.dispose();
        return image;
    }

    private void drawSunrise(Graphics2D g, float angle) {
        float[] colors = sunriseSunset(angle);
        if (colors == null) {
            return;
        }
        double phase = angle * Math.PI * 2.0;
        boolean evening = Math.sin(phase) > 0.0;
        float x = evening ? WIDTH * 0.82f : WIDTH * 0.18f;
        float y = HEIGHT * 0.58f;
        Color center = new Color(clamp(colors[0]), clamp(colors[1]), clamp(colors[2]), clamp(colors[3] * 0.82f));
        Color edge = new Color(center.getRed(), center.getGreen(), center.getBlue(), 0);
        RadialGradientPaint paint = new RadialGradientPaint(x, y, WIDTH * 0.42f,
                new float[] {0.0f, 1.0f}, new Color[] {center, edge});
        g.setPaint(paint);
        g.fillRect(0, 0, WIDTH, HEIGHT);
    }

    private void drawStars(Graphics2D g, float angle, float visibility) {
        if (visibility <= 0.03f) {
            return;
        }
        double rotation = angle * Math.PI * 2.0;
        for (Star star : STARS) {
            double x = star.x * Math.cos(rotation) - star.z * Math.sin(rotation);
            double z = star.x * Math.sin(rotation) + star.z * Math.cos(rotation);
            double longitude = Math.atan2(x, z);
            double latitude = Math.asin(star.y);
            if (longitude < -Math.PI * 0.72 || longitude > Math.PI * 0.72 || latitude < -0.18) {
                continue;
            }
            int sx = (int)(WIDTH * (0.5 + longitude / (Math.PI * 1.44)));
            int sy = (int)(HEIGHT * (0.60 - latitude / (Math.PI * 0.95)));
            if (sx < 0 || sx >= WIDTH || sy < 0 || sy >= HEIGHT) {
                continue;
            }
            int alpha = (int)(230 * visibility * (0.75 + star.size));
            int diameter = star.size > 0.22 ? 2 : 1;
            g.setColor(new Color(235, 241, 255, clamp255(alpha)));
            g.fill(new Ellipse2D.Double(sx, sy, diameter, diameter));
        }
    }

    private void drawCelestialBodies(Graphics2D g, float angle, long worldTime, float day) {
        double phase = angle * Math.PI * 2.0;
        drawBody(g, sun, phase, 112, Math.max(0.16f, day));

        int moonPhase = (int)((worldTime / 24000L % 8L + 8L) % 8L);
        int tileWidth = moonPhases.getWidth() / 4;
        int tileHeight = moonPhases.getHeight() / 2;
        int tileX = (moonPhase % 4) * tileWidth;
        int tileY = (moonPhase / 4) * tileHeight;
        BufferedImage moon = moonPhases.getSubimage(tileX, tileY, tileWidth, tileHeight);
        drawBody(g, moon, phase + Math.PI, 92, Math.max(0.18f, 1.0f - day));
    }

    private void drawBody(Graphics2D g, BufferedImage body, double phase, int size, float alpha) {
        double altitude = Math.cos(phase);
        double horizontal = Math.sin(phase);
        int x = (int)(WIDTH * 0.5 + horizontal * WIDTH * 0.42 - size / 2.0);
        int y = (int)(HEIGHT * 0.57 - altitude * HEIGHT * 0.47 - size / 2.0);
        java.awt.Composite old = g.getComposite();
        g.setComposite(AlphaComposite.SrcOver.derive(clamp(alpha, 0.0f, 1.0f)));
        g.drawImage(body, x, y, size, size, null);
        g.setComposite(old);
    }

    private void drawClouds(Graphics2D g, long worldTime, float day, float rainStrength) {
        BufferedImage layer = tint(clouds, blend(new Color(136, 144, 157), Color.WHITE, day), 1.0f);
        int tile = 430;
        BufferedImage scaled = scale(layer, tile, tile);
        int offset = (int)((worldTime * 0.9) % tile);
        java.awt.Composite oldComposite = g.getComposite();
        AffineTransform oldTransform = g.getTransform();
        float alpha = 0.44f + rainStrength * 0.30f;
        g.setComposite(AlphaComposite.SrcOver.derive(alpha));
        g.translate(-offset, HEIGHT * 0.25);
        g.shear(-0.22, 0.0);
        TexturePaint paint = new TexturePaint(scaled, new Rectangle2D.Double(0, 0, tile, tile));
        g.setPaint(paint);
        g.fill(new Rectangle2D.Double(-tile, 0, WIDTH + tile * 3, HEIGHT * 0.48));
        g.setTransform(oldTransform);
        g.setComposite(oldComposite);
    }

    private void drawRain(Graphics2D g, long worldTime, float strength) {
        java.awt.Composite old = g.getComposite();
        g.setComposite(AlphaComposite.SrcOver.derive(clamp(strength * 0.62f, 0.0f, 1.0f)));
        int stripWidth = 96;
        int stripHeight = 384;
        BufferedImage strip = scale(rain, stripWidth, stripHeight);
        int yOffset = (int)((worldTime * 9L) % stripHeight);
        for (int x = -stripWidth; x < WIDTH + stripWidth; x += stripWidth) {
            g.drawImage(strip, x, -stripHeight + yOffset, null);
            g.drawImage(strip, x, yOffset, null);
            g.drawImage(strip, x, stripHeight + yOffset, null);
        }
        g.setComposite(old);
        g.setColor(new Color(19, 24, 32, 55));
        g.fillRect(0, 0, WIDTH, HEIGHT);
    }

    private void drawGroundSilhouette(Graphics2D g, float day, float rainStrength) {
        int y = (int)(HEIGHT * 0.82);
        Color ground = blend(new Color(2, 3, 7), new Color(33, 49, 42), day * (1.0f - rainStrength * 0.6f));
        g.setColor(ground);
        int[] xs = {0, 0, 130, 220, 340, 455, 560, 660, 770, 875, 1010, 1110, 1280, 1280};
        int[] ys = {HEIGHT, y + 12, y - 8, y + 18, y - 20, y + 9, y - 35, y + 13, y - 17, y + 11, y - 26, y + 7, y - 12, HEIGHT};
        g.fillPolygon(xs, ys, xs.length);
    }

    private void drawLabel(Graphics2D g, String label, long worldTime, float angle) {
        g.setColor(new Color(0, 0, 0, 135));
        g.fillRoundRect(24, HEIGHT - 82, 520, 56, 16, 16);
        g.setColor(Color.WHITE);
        g.setFont(new Font(Font.SANS_SERIF, Font.BOLD, 20));
        g.drawString(label, 42, HEIGHT - 52);
        g.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 13));
        g.setColor(new Color(220, 225, 235));
        g.drawString("worldTime=" + worldTime + "  celestialAngle=" + String.format(java.util.Locale.ROOT, "%.6f", angle), 42, HEIGHT - 33);
    }

    private BufferedImage contactSheet(List<Path> images) throws IOException {
        int thumbWidth = 560;
        int thumbHeight = 315;
        int margin = 28;
        int rows = 3;
        BufferedImage sheet = new BufferedImage(thumbWidth * 2 + margin * 3, thumbHeight * rows + margin * 4, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = sheet.createGraphics();
        configure(g);
        g.setColor(new Color(18, 20, 25));
        g.fillRect(0, 0, sheet.getWidth(), sheet.getHeight());
        for (int i = 0; i < images.size(); i++) {
            BufferedImage image = ImageIO.read(images.get(i).toFile());
            int column = i % 2;
            int row = i / 2;
            int x = margin + column * (thumbWidth + margin);
            int y = margin + row * (thumbHeight + margin);
            g.drawImage(image, x, y, thumbWidth, thumbHeight, null);
            g.setColor(new Color(220, 225, 235));
            g.drawRect(x, y, thumbWidth, thumbHeight);
        }
        g.dispose();
        return sheet;
    }

    public static float calculateCelestialAngle(long worldTime, float partialTicks) {
        int i = (int)(worldTime % 24000L);
        float f = ((float)i + partialTicks) / 24000.0f - 0.25f;
        if (f < 0.0f) {
            ++f;
        }
        if (f > 1.0f) {
            --f;
        }
        float f1 = 1.0f - (float)((Math.cos((double)f * Math.PI) + 1.0) / 2.0);
        return f + (f1 - f) / 3.0f;
    }

    private static float[] sunriseSunset(float celestialAngle) {
        float f1 = (float)Math.cos(celestialAngle * Math.PI * 2.0) - 0.0f;
        if (f1 < -0.4f || f1 > 0.4f) {
            return null;
        }
        float f3 = (f1 / 0.4f) * 0.5f + 0.5f;
        float f4 = 1.0f - (1.0f - (float)Math.sin(f3 * Math.PI)) * 0.99f;
        f4 *= f4;
        return new float[] {f3 * 0.3f + 0.7f, f3 * f3 * 0.7f + 0.2f, 0.2f, f4};
    }

    private static Color fogColor(float celestialAngle) {
        float f = (float)Math.cos(celestialAngle * Math.PI * 2.0) * 2.0f + 0.5f;
        f = clamp(f, 0.0f, 1.0f);
        float r = 0.7529412f * (f * 0.94f + 0.06f);
        float g = 0.84705883f * (f * 0.94f + 0.06f);
        float b = 1.0f * (f * 0.91f + 0.09f);
        return new Color(clamp(r), clamp(g), clamp(b));
    }

    private static List<Star> generateStars() {
        Random random = new Random(10842L);
        List<Star> stars = new ArrayList<Star>();
        for (int i = 0; i < 1500; ++i) {
            double x = random.nextFloat() * 2.0f - 1.0f;
            double y = random.nextFloat() * 2.0f - 1.0f;
            double z = random.nextFloat() * 2.0f - 1.0f;
            double size = 0.15f + random.nextFloat() * 0.1f;
            double lengthSquared = x * x + y * y + z * z;
            if (lengthSquared < 1.0 && lengthSquared > 0.01) {
                double inverseLength = 1.0 / Math.sqrt(lengthSquared);
                stars.add(new Star(x * inverseLength, y * inverseLength, z * inverseLength, size));
                random.nextDouble();
            }
        }
        return stars;
    }

    private static BufferedImage load(String path) throws IOException {
        InputStream in = CpuSkyRenderer.class.getClassLoader().getResourceAsStream(path);
        if (in == null) {
            throw new IOException("Missing image resource: " + path);
        }
        try {
            BufferedImage image = ImageIO.read(in);
            if (image == null) {
                throw new IOException("Unsupported image resource: " + path);
            }
            return image;
        } finally {
            in.close();
        }
    }

    private static BufferedImage removeDarkBackground(BufferedImage source) {
        BufferedImage output = new BufferedImage(source.getWidth(), source.getHeight(), BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < source.getHeight(); y++) {
            for (int x = 0; x < source.getWidth(); x++) {
                int rgb = source.getRGB(x, y);
                int r = (rgb >> 16) & 255;
                int g = (rgb >> 8) & 255;
                int b = rgb & 255;
                int alpha = Math.max(r, Math.max(g, b)) < 8 ? 0 : 255;
                output.setRGB(x, y, (alpha << 24) | (r << 16) | (g << 8) | b);
            }
        }
        return output;
    }

    private static BufferedImage tint(BufferedImage source, Color tint, float opacity) {
        BufferedImage output = new BufferedImage(source.getWidth(), source.getHeight(), BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < source.getHeight(); y++) {
            for (int x = 0; x < source.getWidth(); x++) {
                int argb = source.getRGB(x, y);
                int alpha = (argb >>> 24) & 255;
                int r = ((argb >> 16) & 255) * tint.getRed() / 255;
                int g = ((argb >> 8) & 255) * tint.getGreen() / 255;
                int b = (argb & 255) * tint.getBlue() / 255;
                alpha = clamp255((int)(alpha * opacity));
                output.setRGB(x, y, (alpha << 24) | (r << 16) | (g << 8) | b);
            }
        }
        return output;
    }

    private static BufferedImage scale(BufferedImage source, int width, int height) {
        BufferedImage output = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = output.createGraphics();
        g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
        g.drawImage(source, 0, 0, width, height, null);
        g.dispose();
        return output;
    }

    private static Path write(BufferedImage image, Path output) throws IOException {
        ImageIO.write(image, "png", output.toFile());
        return output;
    }

    private static void configure(Graphics2D g) {
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_RENDERING, RenderingHints.VALUE_RENDER_QUALITY);
        g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
    }

    private static Color blend(Color a, Color b, float amount) {
        amount = clamp(amount, 0.0f, 1.0f);
        int r = (int)(a.getRed() + (b.getRed() - a.getRed()) * amount);
        int g = (int)(a.getGreen() + (b.getGreen() - a.getGreen()) * amount);
        int bl = (int)(a.getBlue() + (b.getBlue() - a.getBlue()) * amount);
        return new Color(clamp255(r), clamp255(g), clamp255(bl));
    }

    private static float clamp(float value, float min, float max) {
        return Math.max(min, Math.min(max, value));
    }

    private static int clamp255(int value) {
        return Math.max(0, Math.min(255, value));
    }

    private static float clamp(float value) {
        return clamp(value, 0.0f, 1.0f);
    }

    private static final class Star {
        final double x;
        final double y;
        final double z;
        final double size;

        Star(double x, double y, double z, double size) {
            this.x = x;
            this.y = y;
            this.z = z;
            this.size = size;
        }
    }
}
