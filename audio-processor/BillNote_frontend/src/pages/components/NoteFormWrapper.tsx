import { useForm } from "react-hook-form"
import { Form } from "@/components/ui/form"
import NoteForm from "./NoteForm"

const NoteFormWrapper = () => {
    const form = useForm()

    return (
        <Form {...form}>
            <NoteForm />
        </Form>
    )
}

export default NoteFormWrapper
