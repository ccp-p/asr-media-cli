package main

import (
	"encoding/json"
	"fmt"
	"os" // 使用 os.ReadFile (Go 1.16+)
	"path/filepath"
	"strings"
)

// Course 结构体，根据你的JSON字段调整
// 假设JSON中有 "title", "description" (可能没有), 和 "url" 字段
type Course struct {
    Title       string `json:"title"`
    Description string `json:"description,omitempty"` // 添加 omitempty 以防 description 不存在或为空
    URL         string `json:"url"`                 // 新增 URL 字段
    // 可以添加其他你需要的字段
    // Example: Instructor string `json:"instructor"`
    // Example: Price      float64 `json:"price"`
}

// 定义分类和关键词 (保持不变)
var categoryKeywords = map[string][]string{
    "美食": {"美食", "烹饪", "烘焙", "菜谱", "料理", "食材", "营养", "甜点", "蛋糕", "面包", "咖啡", "调酒", "吃"},
    "编程": {"编程", "代码", "开发", "python", "java", "go", "c++", "javascript", "前端", "后端", "web", "app", "算法", "数据结构", "软件", "程序员", "html", "css", "node.js", "react", "vue", "angular"},
    "AI": {"人工智能", "ai", "机器学习", "深度学习", "nlp", "自然语言处理", "计算机视觉", "大模型", "chatgpt", "tensorflow", "pytorch"},
    "拍摄": {"摄影", "拍摄", "摄像", "照片", "视频", "相机", "单反", "微单", "手机摄影", "构图", "用光", "布光", "人像", "风光"},
    "剪辑": {"剪辑", "编辑", "后期", "premiere", "final cut", "剪映", "davinci", "特效", "vfx", "调色", "vlog", "短视频"},
    "考试": {"公基","事业","事业单位","考试", "考研", "公务员", "国考", "省考", "雅思", "托福", "四级", "六级", "cet", "证书", "认证", "备考", "刷题", "面试", "笔试"},
    "设计": {"设计", "ui", "ux", "平面设计", "插画", "建模", "渲染", "photoshop", "illustrator", "cad", "c4d", "blender", "sketch", "figma", "交互设计", "视觉设计"},
    "音乐": {"音乐", "乐器", "吉他", "钢琴", "唱歌", "声乐", "作曲", "编曲", "乐理", "尤克里里", "鼓", "贝斯"},
    "语言": {"英语", "日语", "韩语", "法语", "德语", "西班牙语", "口语", "听力", "词汇", "语法", "翻译", "外语"},
    "职场": {"职场", "沟通", "管理", "领导力", "效率", "时间管理", "ppt", "excel", "word", "求职", "简历", "面试技巧"},
    "化妆": {"化妆","妆容","护肤","美容","美妆","化妆技巧","化妆教程","化妆品","护肤品","面膜","眼影","口红"},
    // 可以继续添加更多分类...
}

// classifyCourse 函数尝试为单个课程分类 (保持不变)
func classifyCourse(course Course, categories map[string][]string) string {
    // 合并标题和描述，转为小写，方便匹配
    // 如果描述可能为空，需要处理 nil 或空字符串
    content := strings.ToLower(course.Title + " " + course.Description)

    // 遍历定义的分类 (注意：map遍历顺序不固定，如果需要固定优先级，需要用切片等有序结构)
    for category, keywords := range categories {
        for _, keyword := range keywords {
            // 检查关键词（小写）是否存在于内容（小写）中
            if strings.Contains(content, strings.ToLower(keyword)) {
                return category // 找到第一个匹配的分类就返回
            }
        }
    }

    return "其它" // 没有匹配到任何分类
}

func main() {
    // --- 1. 读取文件 --- (保持不变)
    parPath := `D:\download\dest`
    fileName := `ouput.txt` // 修改为你的文件路径
    filePath := filepath.Join(parPath, fileName)
    fmt.Printf("正在读取文件: %s\n", filePath)
    jsonData, err := os.ReadFile(filePath)
    if err != nil {
        fmt.Printf("Error reading file %s: %v\n", filePath, err)
        return
    }

    // --- 2. 解析JSON --- (保持不变, 新的 URL 字段会自动解析)
    var courses []Course
    err = json.Unmarshal(jsonData, &courses)
    if err != nil {
        fmt.Printf("Error unmarshalling JSON: %v\n", err)
        if len(jsonData) > 100 {
            fmt.Println("JSON data start:", string(jsonData[:100]))
        } else {
            fmt.Println("JSON data:", string(jsonData))
        }
        return
    }

    // --- 3. 分类课程 --- (保持不变)
    classifiedCourses := make(map[string][]Course)
    for _, course := range courses {
        category := classifyCourse(course, categoryKeywords)
        classifiedCourses[category] = append(classifiedCourses[category], course)
    }

    // --- 4. 输出结果 --- (保持不变, 输出的 Course 对象现在包含 URL)
    fmt.Println("课程分类结果:")
    fmt.Println("===================================")
    totalClassified := 0
    for category, courseList := range classifiedCourses {
        fmt.Printf("分类: %s (%d门课程)\n", category, len(courseList))
        totalClassified += len(courseList)
        fmt.Println("-----------------------------------")
    }

    fmt.Printf("\n总共处理了 %d 门课程，分类了 %d 门。\n", len(courses), totalClassified)

    // 可选：将分类结果保存为新的JSON文件 (保持不变, 输出的 Course 对象现在包含 URL)
    outputFilePath := "classified_courses.json"
    outputFilePath = filepath.Join(parPath, "classified_courses.json") // 如果需要保存到指定路径
    outputJson, err := json.MarshalIndent(classifiedCourses, "", "  ") // 格式化输出
    if err != nil {
        fmt.Printf("Error marshalling classified courses to JSON: %v\n", err)
    } else {
        err = os.WriteFile(outputFilePath, outputJson, 0644)
        if err != nil {
            fmt.Printf("Error writing classified courses to file %s: %v\n", outputFilePath, err)
        } else {
            fmt.Printf("分类结果已保存到 %s\n", outputFilePath)
        }
    }
}
