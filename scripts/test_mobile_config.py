from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from mobile_config import configure
import pytest
@pytest.mark.parametrize('major',[8,9])
def test_agp_mode_and_preserve_wrapper(tmp_path,major):
    (tmp_path/'app').mkdir()
    (tmp_path/'settings.gradle.kts').write_text(f'id("com.android.application") version "{major}.1.0" apply false')
    (tmp_path/'app/build.gradle.kts').write_text('plugins { id("com.android.application") }')
    (tmp_path/'gradle.properties').write_text('android.newDsl=false\nandroid.builtInKotlin=false\n')
    (tmp_path/'gradlew').write_text('preserved wrapper')
    configure(tmp_path)
    assert (tmp_path/'gradlew').read_text()=='preserved wrapper'
    assert ('android.builtInKotlin=true' in (tmp_path/'gradle.properties').read_text())==(major>=9)
    assert ('org.jetbrains.kotlin.android' in (tmp_path/'app/build.gradle.kts').read_text())==(major<9)
