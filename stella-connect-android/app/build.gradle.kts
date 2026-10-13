plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// ---------------------------------------------------------------------------
// Optional PERSONAL K2 bundle (local/sideload only — never used by CI).
//
//   ./gradlew assembleRelease -PstellaK2Bundle=true \
//       -PstellaK2Model=/path/to/K2-Horizon-0.9B-Q4_K_M.gguf \
//       -PstellaK2Server=/path/to/llama-server \
//       -PstellaSigningStore=/path/to/stella-release.jks \
//       -PstellaSigningPassword=...
//
// With the flag OFF (the default, and what GitHub Actions builds) the APK
// carries no model and no llama-server: K2Manager downloads whatever GGUF the
// user picks. With it ON we stage the local runtime into assets/k2/ so the app
// is offline-capable out of the box.
//
// The flag also switches the applicationId suffix to ".k2" so a personal build
// installs alongside — and never overwrites — the public build.
// ---------------------------------------------------------------------------
val k2Bundle = (project.findProperty("stellaK2Bundle") as String?)?.toBoolean() == true
val k2Model = (project.findProperty("stellaK2Model") as String?) ?: ""
val k2Server = (project.findProperty("stellaK2Server") as String?) ?: ""
val signStore = (project.findProperty("stellaSigningStore") as String?) ?: ""
val signPassword = (project.findProperty("stellaSigningPassword") as String?) ?: ""
val signAlias = (project.findProperty("stellaSigningAlias") as String?) ?: "stella"

if (k2Bundle) {
    require(k2Model.isNotBlank() && File(k2Model).isFile) {
        "stellaK2Bundle=true but stellaK2Model is missing or not a file: '$k2Model'"
    }
    require(k2Server.isNotBlank() && File(k2Server).isFile) {
        "stellaK2Bundle=true but stellaK2Server is missing or not a file: '$k2Server'"
    }
}

// Stage the personal runtime into the asset tree before the Android plugin
// snapshots assets/. Files land in app/src/main/assets/k2/ and are gitignored.
//
// Clearing on the way out matters: a previous local K2 build leaves the assets
// on disk, and the plugin packages whatever is in the folder regardless of the
// flag. Without this, the PUBLIC build silently ships the 666MB model.
val k2AssetsDir = layout.projectDirectory.dir("src/main/assets/k2")
if (k2Bundle) {
    k2AssetsDir.asFile.mkdirs()
    val modelName = File(k2Model).name
    File(k2AssetsDir.asFile, modelName).writeBytes(File(k2Model).readBytes())
    File(k2AssetsDir.asFile, "llama-server").writeBytes(File(k2Server).readBytes())
    File(k2AssetsDir.asFile, "bundled.txt").writeText(modelName)
    logger.lifecycle("stella: staging personal K2 runtime ($modelName) into assets/k2/")
} else if (k2AssetsDir.asFile.exists()) {
    k2AssetsDir.asFile.deleteRecursively()
    logger.lifecycle("stella: public build - removed stale assets/k2 staging")
}

android {
    namespace = "com.stella.connect"
    compileSdk = 35
    buildToolsVersion = "35.0.0"

    defaultConfig {
        applicationId = "com.stella.connect"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"

        if (k2Bundle) {
            applicationIdSuffix = ".k2"
            versionNameSuffix = "-k2local"
            // The bundled llama-server is aarch64 only.
            ndk { abiFilters += listOf("arm64-v8a") }
        }

        buildConfigField("boolean", "K2_BUNDLED", if (k2Bundle) "true" else "false")
        buildConfigField("String", "K2_BUNDLED_MODEL",
            if (k2Bundle) "\"" + File(k2Model).name + "\"" else "\"\"")
        // The PC bridge ships in BOTH variants and is opt-in at runtime: a
        // phone can delegate large-model work to a desktop because most
        // phones cannot run frontier models locally. Public builds therefore
        // need it just as much as the personal one - the difference is only
        // whether a local model already exists.
        buildConfigField("boolean", "BRIDGE_AVAILABLE", "true")
        // Personal builds start with the bridge on; public users opt in.
        buildConfigField("boolean", "BRIDGE_DEFAULT_ON", if (k2Bundle) "true" else "false")

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (signStore.isNotBlank()) {
            create("local") {
                storeFile = file(signStore)
                storePassword = signPassword
                keyAlias = signAlias
                keyPassword = signPassword
            }
        }
    }

    buildTypes {
        release {
            // Sideloading requires a real signature; CI (no keystore) stays unsigned.
            signingConfig = signingConfigs.findByName("local")
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"),
                          "proguard-rules.pro")
        }
    }

    // Keep the two variants on disk side by side: the personal K2 APK must not
    // overwrite the public one (scripts/stella_build.py picks by name).
    applicationVariants.all {
        val variantName = name
        outputs.all {
            val out = this as com.android.build.gradle.internal.api.BaseVariantOutputImpl
            out.outputFileName = if (k2Bundle) {
                "stella-k2-bundled-arm64.apk"
            } else {
                "stella-connect-$variantName.apk"
            }
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    // The GGUF is already entropy-dense: deflating a 600MB+ asset just burns
    // build time and inflates install size. Storing it uncompressed also lets
    // K2Manager mmap it straight out of the APK.
    androidResources {
        noCompress += listOf("gguf")
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.09.00"))
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.core:core-ktx:1.13.1")
    // SplashScreen compat backports the platform splash on API 21-30.
    implementation("androidx.core:core-splashscreen:1.0.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.navigation:navigation-compose:2.8.2")
    debugImplementation("androidx.compose.ui:ui-tooling")
    implementation("com.google.android.material:material:1.12.0")

    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")

    implementation("androidx.camera:camera-camera2:1.4.0")
    implementation("androidx.camera:camera-lifecycle:1.4.0")
    implementation("androidx.camera:camera-view:1.4.0")
    implementation("com.google.mlkit:barcode-scanning:17.3.0")
}