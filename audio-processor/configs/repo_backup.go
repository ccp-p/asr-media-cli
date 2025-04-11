// // repo_backup.go - 在旧电脑上运行
// package main

// import (
//     "encoding/json"
//     "fmt"
//     "io/ioutil"
//     "os"
//     "os/exec"
//     "path/filepath"
//     "strings"
// )

// // 仓库信息结构
// type Repository struct {
//     Path       string `json:"path"`
//     Type       string `json:"type"` // "git" 或 "svn"
//     RemoteURL  string `json:"remote_url"`
//     Branch     string `json:"branch,omitempty"`     // 仅Git
//     HasChanges bool   `json:"has_changes"`          // 是否有未提交的修改
//     Revision   string `json:"revision,omitempty"`   // 仅SVN
// }

// // 备份配置
// type BackupConfig struct {
//     ScanDirs  []string     `json:"scan_dirs"`  // 要扫描的目录
//     Repos     []Repository `json:"repos"`      // 找到的仓库
//     TargetDir string       `json:"target_dir"` // 新电脑上的目标目录
// }

// func main() {
//     // 初始化配置
//     config := BackupConfig{
//         ScanDirs: []string{},
//         Repos:    []Repository{},
//     }

//     // 获取要扫描的目录
//     if len(os.Args) < 2 {
//         fmt.Println("请指定要扫描的目录，例如: go run repo_backup.go D:\\Projects D:\\Work")
//         os.Exit(1)
//     }

//     config.ScanDirs = os.Args[1:]
    
//     // 询问新电脑上的目标目录
//     fmt.Print("请输入新电脑上的目标目录路径 (例如 D:\\Projects): ")
//     fmt.Scanln(&config.TargetDir)
    
//     // 扫描目录查找仓库
//     for _, dir := range config.ScanDirs {
//         fmt.Printf("扫描目录: %s\n", dir)
//         scanDirectory(dir, &config.Repos)
//     }

//     // 保存仓库信息到JSON文件
//     jsonData, err := json.MarshalIndent(config, "", "  ")
//     if err != nil {
//         fmt.Printf("生成JSON失败: %v\n", err)
//         os.Exit(1)
//     }

//     err = ioutil.WriteFile("repositories.json", jsonData, 0644)
//     if err != nil {
//         fmt.Printf("保存JSON文件失败: %v\n", err)
//         os.Exit(1)
//     }

//     // 生成恢复脚本
//     generateRestoreScript()

//     fmt.Printf("\n备份完成! 找到 %d 个仓库。\n", len(config.Repos))
//     fmt.Println("请将 repositories.json 和 repo_restore.go 文件复制到新电脑，然后运行恢复脚本。")
// }

// // 扫描目录查找Git和SVN仓库
// func scanDirectory(dir string, repos *[]Repository) {
//     err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
//         if err != nil {
//             fmt.Printf("访问路径出错 %s: %v\n", path, err)
//             return filepath.SkipDir
//         }

//         if !info.IsDir() {
//             return nil
//         }

//         // 检查是否是Git仓库
//         if _, err := os.Stat(filepath.Join(path, ".git")); err == nil {
//             repo := analyzeGitRepo(path)
//             *repos = append(*repos, repo)
//             fmt.Printf("找到Git仓库: %s\n", path)
//             return filepath.SkipDir // 跳过.git目录内部
//         }

//         // 检查是否是SVN仓库
//         if _, err := os.Stat(filepath.Join(path, ".svn")); err == nil {
//             repo := analyzeSVNRepo(path)
//             *repos = append(*repos, repo)
//             fmt.Printf("找到SVN仓库: %s\n", path)
//             return filepath.SkipDir // 跳过.svn目录内部
//         }

//         return nil
//     })

//     if err != nil {
//         fmt.Printf("扫描目录出错 %s: %v\n", dir, err)
//     }
// }

// // 分析Git仓库信息
// func analyzeGitRepo(path string) Repository {
//     repo := Repository{
//         Path: path,
//         Type: "git",
//     }

//     // 获取远程URL
//     cmd := exec.Command("git", "-C", path, "config", "--get", "remote.origin.url")
//     output, err := cmd.Output()
//     if err == nil {
//         repo.RemoteURL = strings.TrimSpace(string(output))
//     }

//     // 获取当前分支
//     cmd = exec.Command("git", "-C", path, "rev-parse", "--abbrev-ref", "HEAD")
//     output, err = cmd.Output()
//     if err == nil {
//         repo.Branch = strings.TrimSpace(string(output))
//     }

//     // 检查是否有未提交的更改
//     cmd = exec.Command("git", "-C", path, "status", "--porcelain")
//     output, err = cmd.Output()
//     if err == nil && len(output) > 0 {
//         repo.HasChanges = true
//     }

//     return repo
// }

// // 分析SVN仓库信息
// func analyzeSVNRepo(path string) Repository {
//     repo := Repository{
//         Path: path,
//         Type: "svn",
//     }

//     // 获取SVN信息
//     cmd := exec.Command("svn", "info", "--show-item", "url", path)
//     output, err := cmd.Output()
//     if err == nil {
//         repo.RemoteURL = strings.TrimSpace(string(output))
//     }

//     // 获取当前修订版本
//     cmd = exec.Command("svn", "info", "--show-item", "revision", path)
//     output, err = cmd.Output()
//     if err == nil {
//         repo.Revision = strings.TrimSpace(string(output))
//     }

//     // 检查是否有未提交的更改
//     cmd = exec.Command("svn", "status", path)
//     output, err = cmd.Output()
//     if err == nil && len(output) > 0 {
//         repo.HasChanges = true
//     }

//     return repo
// }

// // 生成恢复脚本
// func generateRestoreScript() {
//     // 读取本脚本的恢复部分并写入新文件
//     restoreScript := `
// // repo_restore.go - 在新电脑上运行
// package main

// import (
//     "encoding/json"
//     "fmt"
//     "io/ioutil"
//     "os"
//     "os/exec"
//     "path/filepath"
//     "strings"
// )

// // 仓库信息结构
// type Repository struct {
//     Path       string ` + "`json:\"path\"`" + `
//     Type       string ` + "`json:\"type\"`" + ` // "git" 或 "svn"
//     RemoteURL  string ` + "`json:\"remote_url\"`" + `
//     Branch     string ` + "`json:\"branch,omitempty\"`" + `     // 仅Git
//     HasChanges bool   ` + "`json:\"has_changes\"`" + `          // 是否有未提交的修改
//     Revision   string ` + "`json:\"revision,omitempty\"`" + `   // 仅SVN
// }

// // 备份配置
// type BackupConfig struct {
//     ScanDirs  []string     ` + "`json:\"scan_dirs\"`" + `  // 要扫描的目录
//     Repos     []Repository ` + "`json:\"repos\"`" + `      // 找到的仓库
//     TargetDir string       ` + "`json:\"target_dir\"`" + ` // 新电脑上的目标目录
// }

// func main() {
//     // 读取仓库信息
//     jsonData, err := ioutil.ReadFile("repositories.json")
//     if err != nil {
//         fmt.Printf("读取repositories.json失败: %v\n", err)
//         fmt.Println("请确保repositories.json文件与本脚本在同一目录")
//         os.Exit(1)
//     }

//     var config BackupConfig
//     err = json.Unmarshal(jsonData, &config)
//     if err != nil {
//         fmt.Printf("解析JSON失败: %v\n", err)
//         os.Exit(1)
//     }

//     // 确认目标目录
//     targetDir := config.TargetDir
//     fmt.Printf("将在以下目录恢复仓库: %s\n", targetDir)
//     fmt.Print("是否继续? (y/n): ")
//     var confirm string
//     fmt.Scanln(&confirm)
//     if confirm != "y" && confirm != "Y" {
//         fmt.Println("已取消操作")
//         os.Exit(0)
//     }

//     // 检查Git和SVN是否已安装
//     checkDependencies()

//     // 恢复仓库
//     for i, repo := range config.Repos {
//         fmt.Printf("[%d/%d] 处理仓库: %s\n", i+1, len(config.Repos), repo.Path)

//         // 获取相对路径
//         relPath := getRelativePath(repo.Path, config.ScanDirs)
//         if relPath == "" {
//             fmt.Printf("无法确定相对路径，跳过: %s\n", repo.Path)
//             continue
//         }

//         // 构建新路径
//         newPath := filepath.Join(targetDir, relPath)
        
//         // 确保目录存在
//         err := os.MkdirAll(filepath.Dir(newPath), 0755)
//         if err != nil {
//             fmt.Printf("创建目录失败 %s: %v\n", filepath.Dir(newPath), err)
//             continue
//         }

//         // 克隆/检出仓库
//         if repo.Type == "git" {
//             cloneGitRepo(repo, newPath)
//         } else if repo.Type == "svn" {
//             checkoutSVNRepo(repo, newPath)
//         }
//     }

//     fmt.Println("\n恢复完成!")
//     fmt.Println("注意: 如果有未提交的更改，请查看上面的警告信息。")
// }

// // 检查依赖程序是否已安装
// func checkDependencies() {
//     // 检查Git
//     _, err := exec.LookPath("git")
//     if err != nil {
//         fmt.Println("警告: Git未安装或不在PATH中，无法恢复Git仓库")
//     }

//     // 检查SVN
//     _, err = exec.LookPath("svn")
//     if err != nil {
//         fmt.Println("警告: SVN未安装或不在PATH中，无法恢复SVN仓库")
//     }
// }

// // 获取仓库相对于扫描目录的路径
// func getRelativePath(repoPath string, scanDirs []string) string {
//     for _, scanDir := range scanDirs {
//         if strings.HasPrefix(repoPath, scanDir) {
//             return strings.TrimPrefix(repoPath, scanDir)
//         }
//     }
//     return ""
// }

// // 克隆Git仓库
// func cloneGitRepo(repo Repository, newPath string) {
//     if repo.RemoteURL == "" {
//         fmt.Printf("警告: 仓库没有远程URL，跳过: %s\n", repo.Path)
//         return
//     }

//     // 克隆仓库
//     fmt.Printf("克隆Git仓库: %s\n", repo.RemoteURL)
//     cmd := exec.Command("git", "clone", repo.RemoteURL, newPath)
//     output, err := cmd.CombinedOutput()
//     if err != nil {
//         fmt.Printf("克隆失败: %v\n%s\n", err, output)
//         return
//     }

//     // 切换到指定分支
//     if repo.Branch != "" && repo.Branch != "HEAD" && repo.Branch != "master" && repo.Branch != "main" {
//         fmt.Printf("切换到分支: %s\n", repo.Branch)
//         cmd := exec.Command("git", "-C", newPath, "checkout", repo.Branch)
//         output, err := cmd.CombinedOutput()
//         if err != nil {
//             fmt.Printf("切换分支失败: %v\n%s\n", err, output)
//         }
//     }

//     // 通知未提交的变更
//     if repo.HasChanges {
//         fmt.Printf("警告: 原仓库有未提交的变更，请手动处理: %s\n", repo.Path)
//     }
// }

// // 检出SVN仓库
// func checkoutSVNRepo(repo Repository, newPath string) {
//     if repo.RemoteURL == "" {
//         fmt.Printf("警告: 仓库没有URL，跳过: %s\n", repo.Path)
//         return
//     }

//     // 检出仓库
//     fmt.Printf("检出SVN仓库: %s\n", repo.RemoteURL)
//     cmd := exec.Command("svn", "checkout", repo.RemoteURL, newPath)
//     output, err := cmd.CombinedOutput()
//     if err != nil {
//         fmt.Printf("检出失败: %v\n%s\n", err, output)
//         return
//     }

//     // 通知未提交的变更
//     if repo.HasChanges {
//         fmt.Printf("警告: 原仓库有未提交的变更，请手动处理: %s\n", repo.Path)
//     }
// }
// `

//     err := ioutil.WriteFile("repo_restore.go", []byte(restoreScript), 0644)
//     if err != nil {
//         fmt.Printf("生成恢复脚本失败: %v\n", err)
//     }
// }