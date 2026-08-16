"""
Экспорт собранного поезда (Blueprint со StaticMesh-компонентами) в один FBX
с сохранением взаимного расположения всех деталей.

План А: создать пустой временный уровень, заспавнить BP в нуле координат,
        экспортировать весь уровень в FBX.
План Б (если А недоступен в headless-режиме): открыть карту Subway, найти
        инстанс BP_Train, выделить его (с прикреплёнными акторами) и
        экспортировать только выделенное.
"""
import os

import unreal

BP_PATH = "/Game/Blueprints/Train/BP_Train"
MAP_PATH = "/Game/Maps/Subway"
TMP_LEVEL = "/Game/__TmpTrainExport"
OUT_FBX = os.path.join(
    unreal.SystemLibrary.get_project_directory(), "Exported", "BP_Train.fbx"
)


def export_world_to_fbx(world, selected_only):
    os.makedirs(os.path.dirname(OUT_FBX), exist_ok=True)
    opts = unreal.FbxExportOption()
    opts.collision = False
    opts.level_of_detail = False
    opts.vertex_color = True

    task = unreal.AssetExportTask()
    task.object = world
    task.filename = OUT_FBX
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.selected = selected_only
    task.options = opts

    ok = unreal.Exporter.run_asset_export_task(task)
    for err in task.errors:
        unreal.log_warning(f"  export error: {err}")
    return bool(ok) and os.path.isfile(OUT_FBX)


def get_editor_world():
    try:
        ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if ues:
            return ues.get_editor_world()
    except Exception:
        pass
    return unreal.EditorLevelLibrary.get_editor_world()


def try_new_level():
    try:
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if les and les.new_level(TMP_LEVEL):
            return True
    except Exception as e:
        unreal.log_warning(f"new_level через сабсистему не вышел: {e}")
    try:
        return bool(unreal.EditorLevelLibrary.new_level(TMP_LEVEL))
    except Exception as e:
        unreal.log_warning(f"new_level через EditorLevelLibrary не вышел: {e}")
    return False


def spawn_actor(bp_class):
    try:
        eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        if eas:
            return eas.spawn_actor_from_class(
                bp_class, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0)
            )
    except Exception:
        pass
    return unreal.EditorLevelLibrary.spawn_actor_from_class(
        bp_class, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0)
    )


def plan_a(bp_class):
    unreal.log("План А: временный пустой уровень + спавн BP в (0,0,0)")
    if not try_new_level():
        return False
    actor = spawn_actor(bp_class)
    if actor is None:
        unreal.log_warning("Не удалось заспавнить актора")
        return False
    unreal.log(f"Заспавнен {actor.get_name()}, экспортирую уровень целиком...")
    return export_world_to_fbx(get_editor_world(), selected_only=False)


def plan_b(bp_class):
    unreal.log(f"План Б: открываю карту {MAP_PATH} и ищу инстанс BP_Train")
    world = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    if world is None:
        unreal.log_error("Карта не загрузилась")
        return False

    try:
        eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actors = list(eas.get_all_level_actors())
    except Exception:
        eas = None
        actors = list(unreal.EditorLevelLibrary.get_all_level_actors())

    targets = [a for a in actors if a and a.get_class() == bp_class]
    if not targets:
        targets = [a for a in actors if a and "BP_Train" in a.get_class().get_name()]
    if not targets:
        unreal.log_error("Инстанс BP_Train в карте не найден")
        return False

    selection = list(targets)
    for t in targets:
        try:
            selection.extend(t.get_attached_actors(True, True))
        except Exception:
            pass
    unreal.log(f"Выделяю {len(selection)} актор(ов): {[a.get_name() for a in selection]}")

    try:
        if eas:
            eas.set_selected_level_actors(selection)
        else:
            raise RuntimeError()
    except Exception:
        unreal.EditorLevelLibrary.set_selected_level_actors(selection)

    return export_world_to_fbx(world, selected_only=True)


def main():
    bp_class = unreal.EditorAssetLibrary.load_blueprint_class(BP_PATH)
    if bp_class is None:
        unreal.log_error(f"Не удалось загрузить класс {BP_PATH}")
        return

    ok = plan_a(bp_class)
    if not ok:
        ok = plan_b(bp_class)

    if ok:
        size_mb = os.path.getsize(OUT_FBX) / (1024 * 1024)
        unreal.log(f"=== Готово: {OUT_FBX} ({size_mb:.1f} МБ)")
    else:
        unreal.log_error("=== Экспорт не удался, смотри лог выше")


if __name__ == "__main__":
    main()
