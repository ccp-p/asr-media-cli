import axios from "axios"

const request = axios.create({
    baseURL: "/api", // 默认请求路径前缀
    timeout: 10000,
})

export default request