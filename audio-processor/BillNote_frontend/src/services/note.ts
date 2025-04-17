import request from "@/utils/request"
import toast from 'react-hot-toast'
import {useTaskStore} from "@/store/taskStore";
import request from "@/utils/request"
interface GenerateNotePayload {
    video_url: string
    platform: "bilibili" | "youtube"
    quality: "fast" | "medium" | "slow"
}

export const generateNote = async (data: {
    video_url: string;
    link: undefined | boolean;
    screenshot: undefined | boolean;
    platform: string;
    quality: string
}) => {
    try {
        const response = await request.post("/generate_note", data)

        if (response.data.code!=0){
            if (response.data.msg){
                toast.error(response.data.msg)

            }
            return null
        }
        toast.success("笔记生成任务已提交！")

        const taskId = response.data.data.task_id

        console.log('res',response)
        // 成功提示
        useTaskStore.getState().addPendingTask(taskId, data.platform)

        return response.data
    } catch (e: any) {
        console.error("❌ 请求出错", e)

        // 错误提示
        toast.error(
             "笔记生成失败，请稍后重试"
        )

        throw e // 抛出错误以便调用方处理
    }
}



export const delete_task = async ({video_id, platform}) => {
    try {
        const data={
            video_id,platform
        }
        const res = await request.post("/delete_task",
            data
        )

        if (res.data.code === 0) {
            toast.success("任务已成功删除")
            return res.data
        } else {
            toast.error(res.data.message || "删除失败")
            throw new Error(res.data.message || "删除失败")
        }
    } catch (e) {
        toast.error("请求异常，删除任务失败")
        console.error("❌ 删除任务失败:", e)
        throw e
    }
}


export const get_task_status=async (task_id:string)=>{
    try {
        const response = await request.get("/task_status/"+task_id)

        if (response.data.code==0 && response.data.status=='SUCCESS') {
            // toast.success("笔记生成成功")
        }
        console.log('res',response)
        // 成功提示

        return response.data
    }
    catch (e){
        console.error("❌ 请求出错", e)

        // 错误提示
        toast.error(
            "笔记生成失败，请稍后重试"
        )

        throw e // 抛出错误以便调用方处理
    }
}