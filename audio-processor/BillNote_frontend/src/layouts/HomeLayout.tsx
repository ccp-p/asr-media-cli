import type { FC, ReactNode } from 'react'
import { Button } from "@/components/ui/button.tsx"

interface HomeLayoutProps {
    form: ReactNode
    preview: ReactNode
}

const HomeLayout: FC<HomeLayoutProps> = ({ form, preview }) => {
    return (
        <div className="min-h-screen  flex flex-col bg-white">
            <div className="flex flex-1">
                {/* 左侧部分：Header + 表单 */}
                <aside className="w-[400px] bg-white border-r border-neutral-200 flex flex-col">
                    {/* Header */}
                    <header className="h-16  flex items-center px-6 gap-2">
                        <div className="w-10 h-10 rounded-2xl overflow-hidden flex justify-center items-center">
                            <img src="/icon.svg" alt="logo" className="w-full h-full object-contain" />
                        </div>
                        <div className="text-2xl font-bold text-gray-800">BiliNote</div>
                    </header>

                    {/* 表单内容 */}
                    <div className="flex-1 p-4 overflow-auto">
                        {form}
                    </div>
                </aside>

                {/* 右侧预览区域 */}
                <main className="flex-1 h-screen p-6 bg-white overflow-hidden">
                    {preview}
                </main>
            </div>

            {/* 页脚 */}
            {/*<footer className="h-12 bg-white shadow-inner flex items-center justify-center text-sm text-neutral-600">*/}
            {/*    © 2025 BiliNote. All rights reserved.*/}
            {/*</footer>*/}
        </div>
    )
}

export default HomeLayout
