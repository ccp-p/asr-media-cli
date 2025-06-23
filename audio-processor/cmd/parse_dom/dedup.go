package main

import (
    "encoding/json"
    "flag"
    "fmt"
    "io/ioutil"
    "log"
    "sort"
    "strings"
)

// CourseItem 单个课程项目
type CourseItem struct {
    Title string `json:"title"`
    URL   string `json:"url"`
}

// Course 课程分类结构体
type Course struct {
    AI   []CourseItem `json:"AI"`
    QiTa []CourseItem `json:"其它"`      // 其它 -> QiTa
    JianJi []CourseItem `json:"剪辑"`    // 剪辑 -> JianJi  
    HuaZhuang []CourseItem `json:"化妆"`  // 化妆 -> HuaZhuang
    PaiShe []CourseItem `json:"拍摄"`    // 拍摄 -> PaiShe
    BianCheng []CourseItem `json:"编程"`  // 编程 -> BianCheng
    MeiShi []CourseItem `json:"美食"`    // 美食 -> MeiShi
    KaoShi []CourseItem `json:"考试"`    // 考试 -> KaoShi
    ZhiChang []CourseItem `json:"职场"`   // 职场 -> ZhiChang
    SheJi []CourseItem `json:"设计"`     // 设计 -> SheJi
    YuYan []CourseItem `json:"语言"`     // 语言 -> YuYan
    YinYue []CourseItem `json:"音乐"`    // 音乐 -> YinYue
}

func main() {
    var (
        inputFile  = flag.String("input", `D:\download\dest\xxzl_classified_courses.json`, "输入的JSON文件路径")
        outputFile = flag.String("output", `D:\download\dest\xxzl_classified_courses_dedup.json`, "输出的JSON文件路径")
        action     = flag.String("action", "dedup", "操作类型: dedup(去重), stats(统计), format(格式化)")
        dedupBy    = flag.String("dedup-by", "title", "去重依据: title(标题), url(链接), both(标题+链接)")
    )
    flag.Parse()

    switch *action {
    case "dedup":
        if err := dedupCourses(*inputFile, *outputFile, *dedupBy); err != nil {
            log.Fatalf("去重失败: %v", err)
        }
    case "stats":
        if err := showStats(*inputFile); err != nil {
            log.Fatalf("统计失败: %v", err)
        }
    case "format":
        if err := formatCourses(*inputFile, *outputFile); err != nil {
            log.Fatalf("格式化失败: %v", err)
        }
    default:
        log.Fatalf("不支持的操作: %s", *action)
    }
}

// dedupCourses 去除重复课程
func dedupCourses(inputPath, outputPath, dedupBy string) error {
    fmt.Printf("📖 正在读取文件: %s\n", inputPath)
    
    // 读取文件
    data, err := ioutil.ReadFile(inputPath)
    if err != nil {
        return fmt.Errorf("读取文件失败: %v", err)
    }

    // 解析JSON
    var courses Course
    if err := json.Unmarshal(data, &courses); err != nil {
        return fmt.Errorf("解析JSON失败: %v", err)
    }

    // 统计原始数据
    originalCount := countTotalCourses(courses)
    fmt.Printf("📊 原始课程总数: %d\n", originalCount)

    // 去重处理
    dedupedCourses := dedupAllCategories(courses, dedupBy)
    
    // 统计去重后数据
    dedupedCount := countTotalCourses(dedupedCourses)
    fmt.Printf("🎯 去重后课程总数: %d\n", dedupedCount)
    fmt.Printf("🗑️  移除重复课程: %d\n", originalCount-dedupedCount)

    // 保存结果
    outputData, err := json.MarshalIndent(dedupedCourses, "", "  ")
    if err != nil {
        return fmt.Errorf("序列化JSON失败: %v", err)
    }

    if err := ioutil.WriteFile(outputPath, outputData, 0644); err != nil {
        return fmt.Errorf("写入文件失败: %v", err)
    }

    fmt.Printf("✅ 去重完成! 结果已保存到: %s\n", outputPath)
    return nil
}

// dedupAllCategories 对所有分类进行去重
// dedupAllCategories 对所有分类进行去重
func dedupAllCategories(courses Course, dedupBy string) Course {
    return Course{
        AI:        dedupCourseSlice(courses.AI, dedupBy),
        QiTa:      dedupCourseSlice(courses.QiTa, dedupBy),
        JianJi:    dedupCourseSlice(courses.JianJi, dedupBy),
        HuaZhuang: dedupCourseSlice(courses.HuaZhuang, dedupBy),
        PaiShe:    dedupCourseSlice(courses.PaiShe, dedupBy),
        BianCheng: dedupCourseSlice(courses.BianCheng, dedupBy),
        MeiShi:    dedupCourseSlice(courses.MeiShi, dedupBy),
        KaoShi:    dedupCourseSlice(courses.KaoShi, dedupBy),
        ZhiChang:  dedupCourseSlice(courses.ZhiChang, dedupBy),
        SheJi:     dedupCourseSlice(courses.SheJi, dedupBy),
        YuYan:     dedupCourseSlice(courses.YuYan, dedupBy),
        YinYue:    dedupCourseSlice(courses.YinYue, dedupBy),
    }
}

// dedupCourseSlice 去重课程切片 (修正后的函数)
func dedupCourseSlice(slice []CourseItem, dedupBy string) []CourseItem {
    seen := make(map[string]bool)
    var result []CourseItem

    for _, item := range slice {
        // 根据去重依据生成唯一键
        var key string
        switch dedupBy {
        case "title":
            key = cleanTitle(item.Title)
        case "url":
            key = strings.TrimSpace(item.URL)
        case "both":
            key = cleanTitle(item.Title) + "|" + strings.TrimSpace(item.URL)
        default:
            key = cleanTitle(item.Title) // 默认按标题去重
        }

        if key == "" {
            continue // 跳过空的键
        }

        // 去重逻辑
        if !seen[key] {
            seen[key] = true
            result = append(result, item)
        }
    }

    // 按标题排序结果
    sort.Slice(result, func(i, j int) bool {
        return cleanTitle(result[i].Title) < cleanTitle(result[j].Title)
    })

    return result
}

// cleanTitle 清理标题，用于更准确的去重
func cleanTitle(title string) string {
    // 移除常见前缀和后缀
    prefixes := []string{"【资料】", "名称：", "《", "》", "[", "]", "（", "）", "(", ")"}
    
    cleaned := strings.TrimSpace(title)
    for _, prefix := range prefixes {
        cleaned = strings.TrimPrefix(cleaned, prefix)
        cleaned = strings.TrimSuffix(cleaned, prefix)
        cleaned = strings.TrimSpace(cleaned)
    }
    
    // 转换为小写进行比较
    return strings.ToLower(cleaned)
}

// countTotalCourses 统计总课程数
func countTotalCourses(courses Course) int {
    return len(courses.AI) + len(courses.QiTa) + len(courses.JianJi) + 
           len(courses.HuaZhuang) + len(courses.PaiShe) + len(courses.BianCheng) + 
           len(courses.MeiShi) + len(courses.KaoShi) + len(courses.ZhiChang) + 
           len(courses.SheJi) + len(courses.YuYan) + len(courses.YinYue)
}
// showStats 显示统计信息
func showStats(inputPath string) error {
    data, err := ioutil.ReadFile(inputPath)
    if err != nil {
        return fmt.Errorf("读取文件失败: %v", err)
    }

    var courses Course
    if err := json.Unmarshal(data, &courses); err != nil {
        return fmt.Errorf("解析JSON失败: %v", err)
    }

    fmt.Println("\n📊 课程分类统计:")
    fmt.Println(strings.Repeat("=", 50))
    
    categories := []struct {
        name  string
        count int
        items []CourseItem
    }{
        {"AI", len(courses.AI), courses.AI},
        {"其它", len(courses.QiTa), courses.QiTa},           // 修改这里
        {"剪辑", len(courses.JianJi), courses.JianJi},       // 修改这里
        {"化妆", len(courses.HuaZhuang), courses.HuaZhuang}, // 修改这里
        {"拍摄", len(courses.PaiShe), courses.PaiShe},       // 修改这里
        {"编程", len(courses.BianCheng), courses.BianCheng}, // 修改这里
        {"美食", len(courses.MeiShi), courses.MeiShi},       // 修改这里
        {"考试", len(courses.KaoShi), courses.KaoShi},       // 修改这里
        {"职场", len(courses.ZhiChang), courses.ZhiChang},   // 修改这里
        {"设计", len(courses.SheJi), courses.SheJi},         // 修改这里
        {"语言", len(courses.YuYan), courses.YuYan},         // 修改这里
        {"音乐", len(courses.YinYue), courses.YinYue},       // 修改这里
    }
    total := 0
    for _, cat := range categories {
        fmt.Printf("%-6s: %4d 门课程", cat.name, cat.count)
        if cat.count > 0 {
            fmt.Printf(" (示例: %s)", truncateString(cat.items[0].Title, 30))
        }
        fmt.Println()
        total += cat.count
    }
    
    fmt.Println(strings.Repeat("=", 50))
    fmt.Printf("总计: %d 门课程\n", total)
    
    return nil
}

// truncateString 截断字符串
func truncateString(s string, maxLen int) string {
    if len(s) <= maxLen {
        return s
    }
    return s[:maxLen-3] + "..."
}

// formatCourses 格式化课程数据
func formatCourses(inputPath, outputPath string) error {
    data, err := ioutil.ReadFile(inputPath)
    if err != nil {
        return fmt.Errorf("读取文件失败: %v", err)
    }

    var courses Course
    if err := json.Unmarshal(data, &courses); err != nil {
        return fmt.Errorf("解析JSON失败: %v", err)
    }

    // 格式化输出
    outputData, err := json.MarshalIndent(courses, "", "  ")
    if err != nil {
        return fmt.Errorf("序列化JSON失败: %v", err)
    }

    if err := ioutil.WriteFile(outputPath, outputData, 0644); err != nil {
        return fmt.Errorf("写入文件失败: %v", err)
    }

    fmt.Printf("✅ 格式化完成! 结果已保存到: %s\n", outputPath)
    return nil
}