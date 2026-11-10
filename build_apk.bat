@echo off
setlocal
set ANDROID_HOME=C:\Users\USER\.stella-toolchain\android-sdk
set ANDROID_SDK_ROOT=C:\Users\USER\.stella-toolchain\android-sdk
set JAVA_HOME=C:\Program Files\Java\jdk-17
set PATH=%ANDROID_HOME%\platform-tools;%ANDROID_HOME%\build-tools\35.0.0;%JAVA_HOME%\bin;%PATH%

cd /d "E:\Projects\stella\android"

echo ============================================
echo   STEP 1: Building Android APK
echo ============================================
call gradlew.bat assembleRelease --no-daemon

if %ERRORLEVEL% neq 0 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ============================================
echo   STEP 2: Signing APK
echo ============================================
"C:\Program Files\Java\jdk-17\bin\jarsigner.exe" -verbose -sigalg SHA256withRSA -digestalg SHA-256 ^
  -keystore "C:\Users\USER\.stella-toolchain\stella-personal.jks" ^
  -storepass "StellaPersonal2026Key9x7" ^
  -signedjar app-release-signed.apk ^
  app\build\outputs\apk\release\app-release-unsigned.apk ^
  stella

"C:\Users\USER\.stella-toolchain\android-sdk\build-tools\35.0.0\zipalign.exe" -v -p 4 stella-release-signed.apk stella-release-final.apk

echo.
echo ============================================
echo   STEP 3: Installing on Android Device
echo ============================================
"C:\Users\USER\.stella-toolchain\android-sdk\platform-tools\adb.exe" install -r stella-release-final.apk

echo.
echo ============================================
echo   DONE! Stella APK installed on your device
echo ============================================
pause
