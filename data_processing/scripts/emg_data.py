
import pandas as pd
from datetime import datetime, timedelta
import csv




def emg_data_processing_upsampling(input_file_path, output_file_path):


    # 步骤1: 读取CSV文件
    data = pd.read_csv(input_file_path)
    data=data.replace(",",".")
    data = data[data.iloc[:, 1] != 0]
    

    # 步骤2: 获取所有时间戳并转换为datetime对象
    timestamps = data['Timestamp']
    timestamps = [datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f') for ts in timestamps]

    # 初始化一个空的列表来保存新计算的时间戳
    new_timestamps = []
    
    # 初始化起始点
    start_index = 0

    while start_index < len(timestamps) - 1:
        start_timestamp = timestamps[start_index]
        end_index = start_index + 1
        
        # 查找下一个不同的时间戳
        while end_index < len(timestamps) and timestamps[end_index] == start_timestamp:
            end_index += 1
        
        if end_index < len(timestamps):
            end_timestamp = timestamps[end_index]
            segment_length = end_index - start_index
            interval = (end_timestamp - start_timestamp) / segment_length

            # 为当前段生成新的时间戳
            for i in range(segment_length):
                new_timestamp = start_timestamp + i * interval
                new_timestamps.append(new_timestamp)
        
        start_index = end_index
    
    # 添加最后一个时间戳
    if len(new_timestamps) < len(timestamps):
        new_timestamps.append(timestamps[-1])
    
   # 使用最后一个已知的时间间隔填充缺失的时间戳
    while len(new_timestamps) < len(data) and interval is not None:
        new_timestamp = new_timestamps[-1] + interval
        new_timestamps.append(new_timestamp)

    # 将datetime对象转换回字符串格式，精确到毫秒
    new_timestamps_str = [t.strftime('%Y-%m-%d %H:%M:%S.%f') for t in new_timestamps]

    # 步骤3: 使用新的时间戳更新DataFrame
    data.loc[:, 'Timestamp'] = new_timestamps_str

    # 步骤4: 保存修改后的数据到新的CSV文件
    data.to_csv(output_file_path, index=False)

    print(f"EMG_data: Timestamps have been equalized, and the file has been generated: {output_file_path}")



