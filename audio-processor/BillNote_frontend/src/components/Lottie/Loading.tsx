import { FC } from 'react'
import Lottie from 'lottie-react'
import loadingJson from '@/assets/Lottie/loading.json'

const Loading: FC = () => {
    return (
        <div className="flex justify-center items-center ">
            <Lottie
                animationData={loadingJson}
                loop
                autoplay
                style={{ width: 150, height: 150 }}
            />
        </div>
    )
}

export default Loading
