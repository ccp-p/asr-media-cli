import React,{FC,useEffect,useState}  from "react";
import HomeLayout from "@/layouts/HomeLayout.tsx";
import NoteForm from '@/pages/components/NoteForm'
import MarkdownViewer from '@/pages/components/MarkdownViewer'
import NoteFormWrapper from "@/pages/components/NoteFormWrapper.tsx";
import {get_task_status} from "@/services/note.ts";
import {useTaskStore} from "@/store/taskStore";
type ViewStatus = 'idle' | 'loading' | 'success'
export const HomePage:FC =()=>{
    const tasks = useTaskStore((state) => state.tasks)
    const currentTaskId = useTaskStore((state) => state.currentTaskId)

    const currentTask = tasks.find((t) => t.id === currentTaskId)

    const [status, setStatus] = useState<ViewStatus>('idle')

    const content = currentTask?.markdown || ''

    useEffect(() => {
        if (!currentTask) {
            setStatus('idle')
        } else if (currentTask.status === 'PENDING') {
            setStatus('loading')
        } else if (currentTask.status === 'SUCCESS') {
            setStatus('success')
        }
    }, [currentTask])

    // useEffect( () => {
    //     get_task_status('d4e87938-c066-48a0-bbd5-9bec40d53354').then(res=>{
    //         console.log('res1',res)
    //         setContent(res.data.result.markdown)
    //     })
    // }, [tasks]);
    return (
        <HomeLayout
            form={<NoteForm/>}
            preview={<MarkdownViewer status={status} content={content} />}

        />
    )
}