import pandas as pd
import os

def initialize_csv(read_file_path,save_file_path):
    """
    初始化一个空的CSV文件。
    如果文件已存在，则不进行任何操作。
    
    参数:
    file_path -- 要初始化的CSV文件的路径
    """
    if not os.path.isfile(save_file_path):
        # 直接在读取时获取列头，无需先转换为DataFrame再保存
        df = pd.read_csv(read_file_path, nrows=0)
        # 使用获取的列头创建并保存一个新的空DataFrame
        df.to_csv(save_file_path, index=False)
        print(f"Initialized empty CSV file with headers from {read_file_path} at {save_file_path}")
    else:
        print(f"CSV file already exists at {save_file_path}")

def append_data_to_csv(data_file_path, output_file_path):
    """
    将新的CSV文件数据追加到已有的CSV文件。
    
    参数:
    data_file_path -- 新的CSV数据文件的路径
    output_file_path -- 已有的CSV文件的路径，新数据将追加到这个文件
    """
    # 读取新的CSV文件数据
    new_data = pd.read_csv(data_file_path)
    
    # 检查新数据不为空
    if not new_data.empty:
        # 读取已有的CSV内容到DataFrame
        if os.path.exists(output_file_path):
            combined_csv = pd.read_csv(output_file_path)
        else:
            combined_csv = pd.DataFrame()
        
        # 追加新数据并保存
        combined_csv = combined_csv._append(new_data, ignore_index=True)
        combined_csv.to_csv(output_file_path, index=False)
        print(f"Appended data from {data_file_path} to {output_file_path}")
    else:
        print(f"No data to append from {data_file_path}")

if __name__ == '__main__':
    participant_num = 2
    test_num = 6  #the rounds of the task
    output_file = f'../data/output_data/overall/all_data_P{participant_num}.csv'
    for i in range(1, test_num + 1):
        input_file = f'../data/output_data/{i}/integration_data_P{participant_num}_m.csv'
        if i == 1:
            initialize_csv(input_file,output_file)
            pass
        append_data_to_csv(input_file, output_file)
    