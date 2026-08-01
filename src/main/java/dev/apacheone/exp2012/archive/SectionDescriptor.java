package dev.apacheone.exp2012.archive;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

public final class SectionDescriptor {
    private final String resourcePath;
    private final String sourcePath;
    private final String sha256;
    private final int sectionCount;

    public SectionDescriptor(String resourcePath, String sourcePath, String sha256, int sectionCount) {
        this.resourcePath = resourcePath;
        this.sourcePath = sourcePath;
        this.sha256 = sha256;
        this.sectionCount = sectionCount;
    }

    public String getResourcePath() {
        return resourcePath;
    }

    public String getSourcePath() {
        return sourcePath;
    }

    public String getSha256() {
        return sha256;
    }

    public int getSectionCount() {
        return sectionCount;
    }

    public String loadText() throws IOException {
        InputStream in = SectionDescriptor.class.getClassLoader().getResourceAsStream(resourcePath);
        if (in == null) {
            throw new IOException("Missing section resource: " + resourcePath);
        }
        try {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buffer = new byte[8192];
            int read;
            while ((read = in.read(buffer)) >= 0) {
                out.write(buffer, 0, read);
            }
            return new String(out.toByteArray(), StandardCharsets.UTF_8);
        } finally {
            in.close();
        }
    }
}
