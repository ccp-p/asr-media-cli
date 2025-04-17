import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import { Info,Clock } from "lucide-react"

import {Tooltip, TooltipContent, TooltipProvider, TooltipTrigger} from "@/components/ui/tooltip.tsx";
import {generateNote} from "@/services/note.ts";
import {useTaskStore} from "@/store/taskStore";
import { useState } from "react"
import NoteHistory from "@/pages/components/NoteHistory.tsx";

// ✅ 定义表单 schema
const formSchema = z.object({
    video_url: z.string().url("请输入正确的视频链接"),
    platform: z.string().nonempty("请选择平台"),
    quality: z.enum(["fast", "medium", "slow"], {
        required_error: "请选择音频质量",
    }),
    screenshot: z.boolean().optional(),
    link:z.boolean().optional(),
})


type NoteFormValues = z.infer<typeof formSchema>

const NoteForm = () => {
    const [selectedTaskId] = useState<string | null>(null)

    const tasks = useTaskStore((state) => state.tasks)
    const setCurrentTask=useTaskStore((state)=>state.setCurrentTask)
    const currentTaskId=useTaskStore(state=>state.currentTaskId )
    tasks.find((t) => t.id === selectedTaskId);
    const form = useForm<NoteFormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            video_url: "",
            platform: "bilibili",
            quality: "medium", // 默认中等质量
            screenshot: false,
        },
    })


    const isGenerating = false

    const onSubmit = async (data: NoteFormValues) => {
        console.log("🎯 提交内容：", data)
        await generateNote({
            video_url: data.video_url,
            platform: data.platform,
            quality: data.quality,
            screenshot:data.screenshot,
            link:data.link
        });
    }

    return (
        <div className="flex flex-col h-full">
            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    <div className="space-y-2">
                        <div className="flex items-center justify-between my-3">
                            <h2 className="block  ">视频链接</h2>
                            <TooltipProvider>
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <Info className="h-4 w-4 text-neutral-400 hover:text-primary cursor-pointer" />
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        <p className="text-xs ">输入视频链接，支持哔哩哔哩、YouTube等平台</p>
                                    </TooltipContent>
                                </Tooltip>
                            </TooltipProvider>
                        </div>

                        <div className="flex gap-2">
                            {/* 平台选择 */}
                            <FormField
                                control={form.control}
                                name="platform"
                                render={({ field }) => (
                                    <FormItem>
                                        <Select
                                            onValueChange={field.onChange}
                                            defaultValue={field.value}
                                        >
                                            <FormControl>
                                                <SelectTrigger className="w-32">
                                                    <SelectValue placeholder="选择平台" />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                <SelectItem value="bilibili">哔哩哔哩</SelectItem>
                                                <SelectItem value="youtube">Youtube</SelectItem>
                                                {/*<SelectItem value="local">本地视频</SelectItem>*/}
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            {/* 视频地址 */}
                            <FormField
                                control={form.control}
                                name="video_url"
                                render={({ field }) => (
                                    <FormItem className="flex-1">
                                        <FormControl>
                                            <Input
                                                placeholder="视频链接"
                                                {...field}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                        </div>
                        {/*<p className="text-xs text-neutral-500">*/}
                        {/*    支持哔哩哔哩视频链接，例如：*/}
                        {/*    https://www.bilibili.com/video/BV1vc25YQE9X/*/}
                        {/*</p>*/}
                        <FormField
                            control={form.control}
                            name="quality"
                            render={({ field }) => (
                                <FormItem>
                                    <div className="flex items-center justify-between my-3">
                                        <h2 className="block  ">音频质量</h2>
                                        <TooltipProvider>
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <Info className="h-4 w-4 text-neutral-400 hover:text-primary cursor-pointer" />
                                                </TooltipTrigger>
                                                <TooltipContent>
                                                    <p className="text-xs max-w-[200px]">质量越高，下载体积越大，速度越慢</p>
                                                </TooltipContent>
                                            </Tooltip>
                                        </TooltipProvider>
                                    </div>
                                    <Select
                                        onValueChange={field.onChange}
                                        defaultValue={field.value}
                                    >
                                        <FormControl>
                                            <SelectTrigger className="w-full">
                                                <SelectValue placeholder="选择质量" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            <SelectItem value="fast">快速（压缩）</SelectItem>
                                            <SelectItem value="medium">中等（推荐）</SelectItem>
                                            <SelectItem value="slow">高质量（清晰）</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    {/*<FormDescription className="text-xs text-neutral-500">*/}
                                    {/*    质量越高，下载体积越大，速度越慢*/}
                                    {/*</FormDescription>*/}
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                    </div>

                    {/* 是否需要原片位置 */}
                    <FormField
                        control={form.control}
                        name="link"
                        render={({ field }) => (
                            <FormItem className="flex items-center space-x-2">
                                {/* Tooltip 部分 */}


                                <FormControl>
                                    <Checkbox
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                        id="link"
                                    />
                                </FormControl>

                                <FormLabel
                                    htmlFor="link"
                                    className="text-sm font-medium leading-none"
                                >
                                    是否插入内容跳转链接
                                </FormLabel>
                            </FormItem>
                        )}
                    />
                    {/* 是否需要下载 */}
                    <FormField
                        control={form.control}
                        name="screenshot"
                        render={({ field }) => (
                            <FormItem className="flex items-center space-x-2">
                                {/* Tooltip 部分 */}


                                <FormControl>
                                    <Checkbox
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                        id="screenshot"
                                    />
                                </FormControl>

                                <FormLabel
                                    htmlFor="screenshot"
                                    className="text-sm font-medium leading-none"
                                >
                                    是否插入视频截图
                                </FormLabel>
                            </FormItem>
                        )}
                    />

                    {/* 提交按钮 */}
                    <Button
                        type="submit"
                        className="w-full bg-primary cursor-pointer"
                    >
                        {isGenerating ? "正在生成…" : "生成笔记"}
                    </Button>
                </form>
            </Form>


            {/*生成历史    */}
            <div className="flex items-center gap-2 my-4">
                <Clock className="h-4 w-4 text-neutral-500" />
                <h2 className="text-base font-medium text-neutral-900">生成历史</h2>
            </div>
            <div className="flex-1 min-h-0 overflow-auto">
                <NoteHistory onSelect={setCurrentTask} selectedId={currentTaskId} />

            </div>

            {/* 添加一些额外的说明或功能介绍 */}
            <div className="mt-6 p-4 bg-primary-light rounded-lg">
                <h3 className="font-medium text-primary mb-2">功能介绍</h3>
                <ul className="text-sm space-y-2 text-neutral-600">
                    <li className="flex items-start gap-2">
                        <span className="text-primary font-bold">•</span>
                        <span>自动提取视频内容，生成结构化笔记</span>
                    </li>
                    <li className="flex items-start gap-2">
                        <span className="text-primary font-bold">•</span>
                        <span>支持多个视频平台，包括哔哩哔哩、YouTube等</span>
                    </li>
                    <li className="flex items-start gap-2">
                        <span className="text-primary font-bold">•</span>
                        <span>一键复制笔记，支持Markdown格式</span>
                    </li>
                    <li className="flex items-start gap-2">
                        <span className="text-primary font-bold">•</span>
                        <span>可选择是否插入图片</span>
                    </li>
                </ul>
            </div>
        </div>
    )
}

export default NoteForm
