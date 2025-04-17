import { useTaskStore } from "@/store/taskStore"
import { FC } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { Trash ,Clock} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

interface NoteHistoryProps {
    onSelect: (taskId: string) => void
    selectedId: string | null
}

const NoteHistory: FC<NoteHistoryProps> = ({ onSelect, selectedId }) => {
    const tasks = useTaskStore((state) => state.tasks)
    const removeTask = useTaskStore((state) => state.removeTask)

    if (tasks.length === 0) {
        return (
            <div className="text-center py-6 bg-neutral-50 rounded-md border border-neutral-200">
                <p className="text-sm text-neutral-500">暂无历史记录</p>
            </div>
        )
    }

    return (
        <ScrollArea className="h-auto max-h-[20vh] sm:max-h-[10vh]">

        <div className="flex flex-col space-y-2">
                {tasks.map((task) => (
                    <div
                        key={task.id}
                        className={cn(
                            "flex items-center gap-4 p-3 cursor-pointer transition hover:bg-neutral-50 rounded-md border",
                            selectedId === task.id && "border-primary bg-primary-light"
                        )}
                        onClick={() => onSelect(task.id)}
                    >
                        {/* 封面图 */}
                        <img
                            src={task.audioMeta.cover_url
                                ? `/api/image_proxy?url=${encodeURIComponent(task.audioMeta.cover_url)}`
                                : "/placeholder.png"}
                            alt="封面"
                            className="w-16 h-10 object-cover rounded-md"
                        />

                        {/* 标题 + 状态 */}

                        <div className="flex items-center justify-between gap-2 min-w-0 w-full">
                            <TooltipProvider>
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <div className="font-medium max-w-[120px] truncate flex-1">{task.audioMeta.title || "未命名笔记"}</div>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        <p>{task.audioMeta.title || "未命名笔记"}</p>
                                    </TooltipContent>
                                </Tooltip>
                            </TooltipProvider>
                            <div className="shrink-0">
                                {task.status === "SUCCESS" && <Badge variant="default">已完成</Badge>}
                                {task.status === "PENDING" && <Badge variant="outline">等待中</Badge>}
                                {task.status === "FAILED" && <Badge variant="destructive">失败</Badge>}
                            </div>
                        </div>


                        {/* 删除按钮 */}
                        <TooltipProvider>
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <Button
                                        type="button"
                                        size="icon"
                                        variant="ghost"
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            removeTask(task.id)
                                        }}
                                        className="shrink-0"
                                    >
                                        <Trash className="w-4 h-4 text-muted-foreground" />
                                    </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                    <p>删除</p>
                                </TooltipContent>
                            </Tooltip>
                        </TooltipProvider>
                    </div>

                ))}
            </div>
        </ScrollArea>
    )
}

export default NoteHistory
