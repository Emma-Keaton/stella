@echo off
setlocal
set ANDROID_HOME=C:\Users\USER\.stella-toolchain\android-sdk
set ANDROID_SDK_ROOT=C:\Users\USER\.stella-toolchain\android-sdk
set JAVA_HOME=C:\Program Files\Java\jdk-17
set PATH=%ANDROID_HOME%\platform-tools;%ANDROID_HOME%\build-tools\35.0.0;%JAVA_HOME%\bin;%PATH%
cd /d "E:\Projects\stella\android"
call "E:\Projects\stella\android\gradlew.bat" assembleRelease