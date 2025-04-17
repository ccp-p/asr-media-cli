// hooks/useTaskPolling.ts
import { useEffect } from "react"
import { useTaskStore } from "@/store/taskStore"
import {get_task_status} from "@/services/note.ts";

export const useTaskPolling = (interval = 3000) => {
    const tasks = useTaskStore(state => state.tasks)
    const updateTaskContent = useTaskStore(state => state.updateTaskContent)
    const removeTask=useTaskStore(state=>state.removeTask)
    useEffect(() => {
        const timer = setInterval(async () => {
            const pendingTasks = tasks.filter(
                (task) => task.status === "PENDING" || task.status === "running"
            )

            for (const task of pendingTasks) {
                try {
                    console.log(task)
                    const res = await get_task_status(task.id)
                    const {status}=res.data

                    if (status && status !== task.status) {
                        if (status === "SUCCESS") {
                            const {  markdown, transcript, audio_meta } = res.data.result

                            updateTaskContent(task.id, {
                                status,
                                markdown,
                                transcript,
                                audioMeta: audio_meta,
                            })
                        } else {
                            updateTaskStatus(task.id, status)
                        }
                    }
                } catch (e) {
                    console.error("❌ 任务轮询失败：", e)
                    removeTask(task.id)

                }
            }
        }, interval)

        return () => clearInterval(timer)
    }, [interval, tasks])
}
