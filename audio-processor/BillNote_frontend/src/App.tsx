
import './App.css'
import {HomePage} from "./pages/Home.tsx";
import {useTaskPolling} from "@/hooks/useTaskPolling.ts";

function App() {
    useTaskPolling(3000) // 每 3 秒轮询一次

    return (
        <>
            <HomePage></HomePage>
        </>
    )
}

export default App
