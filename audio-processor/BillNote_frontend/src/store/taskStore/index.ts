import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import {delete_task} from "@/services/note.ts";

export type TaskStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILD'

export interface AudioMeta {
    cover_url: string
    duration: number
    file_path: string
    platform: string
    raw_info: any
    title: string
    video_id: string
}

export interface Segment {
    start: number
    end: number
    text: string
}

export interface Transcript {
    full_text: string
    language: string
    raw: any
    segments: Segment[]
}

export interface Task {
    id: string
    markdown: string
    transcript: Transcript
    status: TaskStatus
    audioMeta: AudioMeta
    createdAt: string
}

interface TaskStore {
    tasks: Task[]
    currentTaskId: string | null
    platform:string|null
    addPendingTask: (taskId: string, platform: string) => void
    updateTaskContent: (id: string, data: Partial<Omit<Task, "id" | "createdAt">>) => void
    removeTask: (id: string) => void
    clearTasks: () => void
    setCurrentTask: (taskId: string | null) => void
    getCurrentTask: () => Task | null
}

export const useTaskStore = create<TaskStore>()(
    persist(
        (set,get) => ({
            tasks: [],
            currentTaskId: null,

            addPendingTask: (taskId: string,platform: string) =>
                set((state) => ({
                    tasks: [
                        {
                            id: taskId,
                            status: "PENDING",
                            markdown: "",
                            platform:platform,
                            transcript: {
                                full_text: "",
                                language: "",
                                raw: null,
                                segments: [],
                            },
                            createdAt: new Date().toISOString(),
                            audioMeta: {
                                cover_url: "",
                                duration: 0,
                                file_path: "",
                                platform: '',
                                raw_info: null,
                                title: "",
                                video_id: "",
                            },
                        },
                        ...state.tasks,
                    ],
                    currentTaskId: taskId, // 默认设置为当前任务
                })),

            updateTaskContent: (id, data) =>
                set((state) => ({
                    tasks: state.tasks.map((task) =>
                        task.id === id ? { ...task, ...data } : task
                    ),
                })),
            getCurrentTask: () => {
                const currentTaskId = get().currentTaskId
                return get().tasks.find((task) => task.id === currentTaskId) || null
            },
            removeTask: async (id) => {
                const task = get().tasks.find((t) => t.id === id)

                // 更新 Zustand 状态
                set((state) => ({
                    tasks: state.tasks.filter((task) => task.id !== id),
                    currentTaskId: state.currentTaskId === id ? null : state.currentTaskId,
                }))

                // 调用后端删除接口（如果找到了任务）
                if (task) {
                    await delete_task({
                        video_id: task.audioMeta.video_id,
                        platform: task.platform,
                    })
                }
            },


            clearTasks: () => set({ tasks: [], currentTaskId: null }),

            setCurrentTask: (taskId) => set({ currentTaskId: taskId }),
        }),
        {
            name: 'task-storage',
        }
    )
)
