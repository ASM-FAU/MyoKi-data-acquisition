import pandas as pd
from datetime import datetime, timedelta





def swap_columns(csv_file, output_file,swap_table_file = '../data/swap_table.csv'):
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file)

    # Read the swap table (assumes two columns: "From" and "To")
    swap_table = pd.read_csv(swap_table_file, names=['From', 'To'], delimiter='-')

    # Convert "From" and "To" to match the column names in the DataFrame
    swap_table['From'] = swap_table['From'].apply(lambda x: f"FSR{x:02}")
    swap_table['To'] = swap_table['To'].apply(lambda x: f"FSR{x:02}")

    # Perform the swaps
    for _, row in swap_table.iterrows():
        from_col = row['From']
        to_col = row['To']

        if from_col in df.columns and to_col in df.columns:
            # Swap the columns
            df[from_col], df[to_col] = df[to_col], df[from_col]
        else:
            print(f"Warning: Columns {from_col} or {to_col} not found in the CSV.")

    # Save the modified DataFrame to a new CSV file
    df.to_csv(output_file, index=False)
    print(f"Swapped columns saved to {output_file}")


def fmg_data_processing(input_file_path, emg_file_path, output_file_path):

    swap_columns(input_file_path,input_file_path)
    # 步骤1: 读取Timestamp_Log.csv，获取最后一条记录的日期
    #timestamp_log = pd.read_csv(emg_file_path)
    #first_log_timestamp_str = timestamp_log.iloc[1]['Timestamp']
    #first_log_date = datetime.strptime(first_log_timestamp_str, '%Y-%m-%d %H:%M:%S.%f').date()

    # 步骤2: 读取mqtt_data.csv文件
    ##file_path = 'C:/Users/HOU/Desktop/datamerge/2/mqtt_data.csv'
    data = pd.read_csv(input_file_path)
    data = data.drop(columns=["Timestamp"])
    data = data.rename(columns={"Timestamp_win": "Timestamp"})


    # 步骤3: 解析并转换时间戳
    def parse_convert_timestamp(ts, date):
        # 将时间戳转换为字符串，格式为HHMMSSfff
        ts_str = str(ts)
        # 解析时间（没有日期）
        time_obj = datetime.strptime(ts_str, '%H%M%S%f').time()
        timestamp = datetime.combine(date, time_obj)

        # Korrigiere die Zeit um eine Stunde
        timestamp_corrected = timestamp #- timedelta(hours=1)  # Subtrahiere eine Stunde CHANGED
        return timestamp_corrected

    # 应用转换函数，添加日期到每个时间戳
    #data['Timestamp'] = data['Timestamp'].apply(lambda x: parse_convert_timestamp(x, first_log_date))

    # 调整列顺序，将Timestamp移到第一列
    cols = ['Timestamp'] + [col for col in data.columns if col != 'Timestamp']

    data = data[cols]

    # 步骤4: 保存到新的CSV文件
    ##new_file_path = 'C:/Users/HOU/Desktop/datamerge/2_1/fmg_data_2.csv'
    data.to_csv(output_file_path, index=False)

    print(f"FMG_data：Updated file saved to: {output_file_path}")

# Example usage:
if __name__ == "__main__":
    input_file_path = '../data/input_data/1/fmg_data_P1.csv'
    output_file_path = '../data/input_data/1/fmg_data_P1_swapped.csv'
    emg_file_path = '../input_data/1/emg_data_P1.csv'

    swap_columns(input_file_path , output_file_path )
