package dev.apacheone.exp2012;

import dev.apacheone.exp2012.archive.GeneratedSectionRegistry;
import dev.apacheone.exp2012.archive.SectionDescriptor;
import dev.apacheone.exp2012.archive.SourceArchiveVerifier;
import dev.apacheone.exp2012.render.CpuSkyRenderer;

import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

public final class Main {
    private Main() {
    }

    public static void main(String[] args) throws Exception {
        String command = args.length == 0 ? "all" : args[0];
        Path archive = option(args, "--archive", Paths.get("source-export"));
        Path output = option(args, "--output", Paths.get("showcase"));

        if ("verify".equals(command) || "all".equals(command)) {
            SourceArchiveVerifier.Result result = SourceArchiveVerifier.verify(archive);
            System.out.println("Manifest rows: " + result.manifestRows);
            System.out.println("Hash-checked files: " + result.checkedFiles);
            System.out.println("Archived Java files: " + result.javaFiles);
            System.out.println("Canonical section files: " + result.sectionFiles);
            System.out.println("Generated section classes: " + GeneratedSectionRegistry.all().size());
            for (String message : result.messages) {
                System.out.println("VERIFY: " + message);
            }
            if (result.failures != 0) {
                throw new IllegalStateException("Source archive verification failed: " + result.failures + " problem(s)");
            }
            verifyGeneratedSections();
            System.out.println("Archive verification: PASS");
        }

        if ("sections".equals(command)) {
            for (SectionDescriptor descriptor : GeneratedSectionRegistry.all()) {
                System.out.println(descriptor.getSourcePath() + " | sections=" + descriptor.getSectionCount()
                        + " | sha256=" + descriptor.getSha256());
            }
        }

        if ("render".equals(command) || "all".equals(command)) {
            List<Path> images = new CpuSkyRenderer().renderAll(output);
            for (Path image : images) {
                System.out.println("Rendered: " + image);
            }
            System.out.println("CPU render: PASS");
        }
    }

    private static void verifyGeneratedSections() throws Exception {
        for (SectionDescriptor descriptor : GeneratedSectionRegistry.all()) {
            String text = descriptor.loadText();
            if (text.length() == 0) {
                throw new IllegalStateException("Empty generated section resource: " + descriptor.getResourcePath());
            }
        }
    }

    private static Path option(String[] args, String name, Path fallback) {
        for (int i = 0; i + 1 < args.length; i++) {
            if (name.equals(args[i])) {
                return Paths.get(args[i + 1]);
            }
        }
        return fallback;
    }
}
