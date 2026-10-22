"""Apply project-specific Kotlin mode without replacing Gradle wrapper/settings."""
from pathlib import Path
import re

def configure(android: Path):
    settings=android/'settings.gradle.kts'
    text=settings.read_text(encoding='utf-8')
    match=re.search(r'id\("com.android.application"\) version "(\d+)\.',text)
    if not match: raise RuntimeError('Không đọc được AGP trong settings.gradle.kts; giữ file và kiểm tra thủ công')
    major=int(match.group(1))
    build=android/'app/build.gradle.kts'
    content=build.read_text(encoding='utf-8')
    if major<9:
        content=content.replace('id("com.android.application")','id("com.android.application")\n    id("org.jetbrains.kotlin.android")')
    build.write_text(content,encoding='utf-8')
    props=android/'gradle.properties'
    content=props.read_text(encoding='utf-8')
    if major>=9:
        content=re.sub(r'android.builtInKotlin=.*','android.builtInKotlin=true',content)
        if 'android.builtInKotlin=' not in content:content+='\nandroid.builtInKotlin=true\n'
    props.write_text(content,encoding='utf-8')
    print(f'AGP {major}: '+('built-in Kotlin (cần Flutter >=3.47)' if major>=9 else 'Kotlin Gradle Plugin (cần KGP >=2.0)'))
