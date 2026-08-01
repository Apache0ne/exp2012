package dev.apacheone.exp2012.archive;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.List;

public final class SourceArchiveVerifier {
    public static final class Result {
        public int manifestRows;
        public int checkedFiles;
        public int sectionFiles;
        public int javaFiles;
        public int failures;
        public final List<String> messages = new ArrayList<String>();
    }

    private SourceArchiveVerifier() {
    }

    public static Result verify(Path archiveRoot) throws IOException {
        Result result = new Result();
        verifyManifest(archiveRoot.resolve("manifest.tsv"), archiveRoot, result);
        verifyManifest(archiveRoot.resolve("glue").resolve("manifest.tsv"), archiveRoot.resolve("glue"), result);

        result.sectionFiles = countBySuffix(archiveRoot.resolve("sections"), ".txt")
                + countBySuffix(archiveRoot.resolve("glue").resolve("sections").resolve("host-access"), ".txt");
        result.javaFiles = countBySuffix(archiveRoot.resolve("full-files"), ".java")
                + countBySuffix(archiveRoot.resolve("glue").resolve("full-files"), ".java");
        return result;
    }

    private static void verifyManifest(Path manifest, Path destinationRoot, Result result) throws IOException {
        if (!Files.isRegularFile(manifest)) {
            result.failures++;
            result.messages.add("Missing manifest: " + manifest);
            return;
        }

        BufferedReader reader = Files.newBufferedReader(manifest, StandardCharsets.UTF_8);
        try {
            String header = reader.readLine();
            if (header == null) {
                result.failures++;
                result.messages.add("Empty manifest: " + manifest);
                return;
            }
            String[] columns = header.split("\\t", -1);
            int typeIndex = indexOf(columns, "type");
            int destinationIndex = indexOf(columns, "destination");
            int shaIndex = indexOf(columns, "sha256");
            if (destinationIndex < 0 || shaIndex < 0) {
                result.failures++;
                result.messages.add("Manifest schema missing destination/sha256: " + manifest);
                return;
            }

            String line;
            int lineNumber = 1;
            while ((line = reader.readLine()) != null) {
                lineNumber++;
                if (line.trim().isEmpty()) {
                    continue;
                }
                result.manifestRows++;
                String[] fields = line.split("\\t", -1);
                if (fields.length <= Math.max(destinationIndex, shaIndex)) {
                    result.failures++;
                    result.messages.add("Malformed manifest row " + manifest + ":" + lineNumber);
                    continue;
                }
                String expected = fields[shaIndex].trim();
                if (expected.isEmpty() || "-".equals(expected)) {
                    continue;
                }
                Path destination = destinationRoot.resolve(fields[destinationIndex].replace('\\', '/')).normalize();
                if (!destination.startsWith(destinationRoot.normalize())) {
                    result.failures++;
                    result.messages.add("Unsafe destination path: " + fields[destinationIndex]);
                    continue;
                }
                if (!Files.isRegularFile(destination)) {
                    String rowType = typeIndex >= 0 && fields.length > typeIndex ? fields[typeIndex].trim() : "";
                    if ("external-binary".equals(rowType)) {
                        result.messages.add("Optional external binary omitted from slim archive: " + destination);
                        continue;
                    }
                    result.failures++;
                    result.messages.add("Missing manifest destination: " + destination);
                    continue;
                }
                String actual = sha256(destination);
                result.checkedFiles++;
                if (!actual.equalsIgnoreCase(expected)) {
                    result.failures++;
                    result.messages.add("SHA-256 mismatch: " + destination + " expected=" + expected + " actual=" + actual);
                }
            }
        } finally {
            reader.close();
        }
    }

    private static int indexOf(String[] values, String target) {
        for (int i = 0; i < values.length; i++) {
            if (target.equalsIgnoreCase(values[i].trim())) {
                return i;
            }
        }
        return -1;
    }

    private static int countBySuffix(Path root, final String suffix) throws IOException {
        if (!Files.exists(root)) {
            return 0;
        }
        final int[] count = new int[] {0};
        Files.walk(root).forEach(path -> {
            if (Files.isRegularFile(path) && path.getFileName().toString().toLowerCase().endsWith(suffix)) {
                count[0]++;
            }
        });
        return count[0];
    }

    public static String sha256(Path file) throws IOException {
        final MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 is unavailable", e);
        }
        byte[] buffer = new byte[65536];
        java.io.InputStream in = Files.newInputStream(file);
        try {
            int read;
            while ((read = in.read(buffer)) >= 0) {
                digest.update(buffer, 0, read);
            }
        } finally {
            in.close();
        }
        byte[] bytes = digest.digest();
        StringBuilder text = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) {
            text.append(String.format("%02x", value & 0xff));
        }
        return text.toString();
    }
}
