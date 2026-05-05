# mini_storage_skeleton

## Learning Goal
理解任务入队、认领、完成、失败回退。

## Run Command
```bash
python main.py
```

## Expected Output
看到任务状态从 `NEW` 变成 `PROCESSING`，最后变成 `DONE`。

## Mapping Back to Original Project
- Original: `src/hz_bank_aiops/storage/task_store.py`
- Original: `src/hz_bank_aiops/service/runtime.py::process_one_task`

## Notes
这里用内存列表模拟任务表，方便先理解状态流。
