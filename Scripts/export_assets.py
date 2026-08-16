"""
Экспорт всех мешей (FBX) и текстур (PNG/TGA/EXR) из проекта
с сохранением иерархии папок Content Browser.

Запуск в редакторе:
    Tools -> Execute Python Script...  -> выбрать этот файл
    (или в консоли Python:  py "C:/Users/The Witcher/Documents/Unreal Projects/FriendlyAnomaly/Scripts/export_assets.py")

Запуск без редактора:
    Scripts/run_export.bat
"""
import os

import unreal

# ==== настройки ==============================================================
OUTPUT_DIR = os.path.join(unreal.SystemLibrary.get_project_directory(), "Exported")

# Какие папки экспортировать. ["/Game"] — весь проект целиком.
SCAN_PATHS = ["/Game/SubwayTrain"]

# Папки, которые пропустить. Например:
# EXCLUDE_PREFIXES = ["/Game/StarterContent", "/Game/Developers"]
EXCLUDE_PREFIXES = []

MESH_CLASSES = {"StaticMesh", "SkeletalMesh"}
TEXTURE_CLASSES = {"Texture2D"}
TEXTURE_EXTS = ("png", "tga", "exr", "hdr")  # пробуем по очереди, пока не получится
GC_EVERY = 25  # сборка мусора каждые N ассетов, чтобы не съесть всю память
# ============================================================================


def make_fbx_options():
    opts = unreal.FbxExportOption()
    opts.collision = False
    opts.level_of_detail = False
    opts.vertex_color = True
    return opts


def run_export_task(obj, filename, options=None):
    """Экспорт одного ассета без каких-либо диалогов. True = файл создан."""
    task = unreal.AssetExportTask()
    task.object = obj
    task.filename = filename
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    if options is not None:
        task.options = options
    ok = False
    try:
        ok = unreal.Exporter.run_asset_export_task(task)
    except Exception as e:
        unreal.log_warning(f"  exception: {e}")
    return bool(ok) and os.path.isfile(filename)


def output_path(asset_data, ext):
    """/Game/Sub/Dir/Name -> <OUTPUT_DIR>/Sub/Dir/Name.<ext>"""
    pkg = str(asset_data.package_name)
    rel = pkg[len("/Game/"):] if pkg.startswith("/Game/") else pkg.lstrip("/")
    rel_dir = os.path.dirname(rel)
    out_dir = os.path.join(OUTPUT_DIR, rel_dir)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"{asset_data.asset_name}.{ext}")


def collect_assets():
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    try:
        registry.wait_for_completion()
    except AttributeError:
        pass
    registry.scan_paths_synchronous(SCAN_PATHS, force_rescan=False)

    seen = set()
    meshes, textures = [], []
    for scan_path in SCAN_PATHS:
        for ad in registry.get_assets_by_path(scan_path, recursive=True):
            pkg = str(ad.package_name)
            key = f"{pkg}.{ad.asset_name}"
            if key in seen or any(pkg.startswith(p) for p in EXCLUDE_PREFIXES):
                continue
            seen.add(key)
            cls = str(ad.asset_class_path.asset_name)
            if cls in MESH_CLASSES:
                meshes.append(ad)
            elif cls in TEXTURE_CLASSES:
                textures.append(ad)
    return meshes, textures


def main():
    meshes, textures = collect_assets()
    total = len(meshes) + len(textures)
    unreal.log(f"=== Экспорт: {len(meshes)} мешей, {len(textures)} текстур -> {OUTPUT_DIR}")

    fbx_options = make_fbx_options()
    done, failed = 0, []

    with unreal.ScopedSlowTask(total, "Экспорт ассетов...") as slow_task:
        slow_task.make_dialog(True)

        for i, ad in enumerate(meshes + textures):
            if slow_task.should_cancel():
                unreal.log_warning("Отменено пользователем")
                break
            is_mesh = str(ad.asset_class_path.asset_name) in MESH_CLASSES
            name = str(ad.package_name)
            slow_task.enter_progress_frame(1, f"{name}")

            obj = ad.get_asset()
            if obj is None:
                failed.append((name, "не удалось загрузить"))
                continue

            if is_mesh:
                ok = run_export_task(obj, output_path(ad, "fbx"), fbx_options)
            else:
                ok = any(run_export_task(obj, output_path(ad, ext)) for ext in TEXTURE_EXTS)

            if ok:
                done += 1
            else:
                failed.append((name, "экспортер не справился"))

            if (i + 1) % GC_EVERY == 0:
                unreal.SystemLibrary.collect_garbage()
                unreal.log(f"  ... {i + 1}/{total}")

    unreal.SystemLibrary.collect_garbage()

    log_path = os.path.join(OUTPUT_DIR, "_export_log.txt")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Успешно: {done}/{total}\n\nНе экспортировались:\n")
        for name, reason in failed:
            f.write(f"  {name}  ({reason})\n")

    unreal.log(f"=== Готово: {done}/{total}. Проблемные ассеты: {len(failed)} (см. {log_path})")


if __name__ == "__main__":
    main()
