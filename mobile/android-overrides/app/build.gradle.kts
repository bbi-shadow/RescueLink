@file:Suppress("DEPRECATION", "DEPRECATION_ERROR") // Legacy AGP DSL retained by Flutter migration.

plugins {
    id("com.android.application")
    id("dev.flutter.flutter-gradle-plugin")
}
android {
    namespace = "vn.edu.rescuelink.rescue_link"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    defaultConfig {
        applicationId = "vn.edu.rescuelink.rescue_link"
        minSdk = 26
        targetSdk = 35
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }
}
kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}
flutter { source = "../.." }
dependencies {
    implementation("com.google.android.gms:play-services-nearby:19.3.0")
}
