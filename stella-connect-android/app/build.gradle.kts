plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// Plain public build: no bundling, no per-flavour applicationId. Models are
// fetched by the user (HuggingFace download or file-picker import) into the
// shared internal-storage Stella/models/ folder, so the app never needs a PC
// to stage a model or server binary.
val signStore = (project.findProperty("stellaSigningStore") as String?) ?: ""
val signPassword = (project.findProperty("stellaSigningPassword") as String?) ?: ""
val signAlias = (project.findProperty("stellaSigningAlias") as String?) ?: "stella"


android {
    namespace = "com.stella.connect"
    compileSdk = 35
    buildToolsVersion = "35.0.0"

    defaultConfig {
        applicationId = "com.stella.connect"
        minSdk = 26
        targetSdk = 35
        versionCode = 2
        versionName = "0.1.0"



        // The PC bridge ships in BOTH variants and is opt-in at runtime: a
        // phone can delegate large-model work to a desktop because most
        // phones cannot run frontier models locally. Public builds therefore
        // need it just as much as the personal one - the difference is only
        // whether a local model already exists.
        buildConfigField("boolean", "BRIDGE_AVAILABLE", "true")
        // Public builds start with the bridge off; users opt in at runtime.
        buildConfigField("boolean", "BRIDGE_DEFAULT_ON", "false")

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
        // A DEBUGGABLE build signed with the same keystore as release, so it
        // installs as an in-place update over the shipped com.stella.connect.
        create("staging") {
            isDebuggable = true
            signingConfig = signingConfigs.findByName("local")
            isMinifyEnabled = false
            matchingFallbacks += listOf("release")
            versionNameSuffix = "-staging"
        }
    }

    applicationVariants.all {
        val variantName = name
        outputs.all {
            val out = this as com.android.build.gradle.internal.api.BaseVariantOutputImpl
            out.outputFileName = "stella-connect-$variantName.apk"
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
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
        jniLibs {
            // Extract .so files to nativeLibraryDir so LocalEngineManager can
            // exec the shipped server binary from a read-only dir (W^X-safe on
            // Android 10+).
            useLegacyPackaging = true
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
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.6")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.navigation:navigation-compose:2.8.2")
    debugImplementation("androidx.compose.ui:ui-tooling")
    implementation("com.google.android.material:material:1.12.0")

    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    // SAF tree documents (Memory Vault notes destination).
    implementation("androidx.documentfile:documentfile:1.0.0")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")

    implementation("androidx.camera:camera-camera2:1.4.0")
    implementation("androidx.camera:camera-lifecycle:1.4.0")
    implementation("androidx.camera:camera-view:1.4.0")
    implementation("com.google.mlkit:barcode-scanning:17.3.0")
}
