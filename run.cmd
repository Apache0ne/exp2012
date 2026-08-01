@echo off
if not exist build\exp2012-builder.jar python tools\build.py
java -jar build\exp2012-builder.jar all --archive source-export --output showcase
