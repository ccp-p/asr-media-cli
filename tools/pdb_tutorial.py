"""
PDB调试器教程
提供一个简单的例子，帮助您学习如何使用pdb进行调试
"""
import pdb


def calculate_sum(a, b):
    """计算两个数的和"""
    result = a + b
    return result


def calculate_product(a, b):
    """计算两个数的积"""
    result = a * b
    return result


def process_numbers(numbers):
    """处理数字列表"""
    total_sum = 0
    total_product = 1
    
    for i, num in enumerate(numbers):
        print(f"处理第 {i+1} 个数字: {num}")
        total_sum = calculate_sum(total_sum, num)
        total_product = calculate_product(total_product, num)
    
    return total_sum, total_product


def main():
    """主函数"""
    print("=== PDB调试演示 ===")
    print("程序将在下一行暂停，进入调试模式")
    print("常用命令:")
    print("- 按 n 执行下一行")
    print("- 按 s 进入函数内部")
    print("- 按 c 继续直到程序结束或下一个断点")
    print("- 输入 p numbers 查看变量值")
    print("- 按 q 退出调试器")
    
    # 设置断点，程序将在这里暂停
    pdb.set_trace()
    
    # 创建一个数字列表
    numbers = [1, 2, 3, 4, 5]
    
    # 处理数字
    result_sum, result_product = process_numbers(numbers)
    
    # 打印结果
    print(f"数字之和: {result_sum}")
    print(f"数字之积: {result_product}")


if __name__ == "__main__":
    main()
