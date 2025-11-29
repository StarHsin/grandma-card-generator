import os

# 圖片所在資料夾
folder = r"D:\Project\grandma-card-generator\backgrounds\festival_common"   # ← 改成你的資料夾路徑

# 取得所有 health_*.jpg 檔案並依檔名排序
files = [
    f for f in os.listdir(folder)
    if f.lower().startswith("festival_common_") and f.lower().endswith(".jpg")
]
files.sort()  # 依目前檔名排序

print("找到的檔案順序：")
for f in files:
    print(" ", f)

# 第一步：改成暫時檔名，避免跟新檔名衝突
temp_names = []
for f in files:
    old_path = os.path.join(folder, f)
    temp_name = f"__temp__{f}"
    temp_path = os.path.join(folder, temp_name)

    os.rename(old_path, temp_path)
    temp_names.append(temp_name)

# 第二步：依順序改成 health_01.jpg, health_02.jpg, ...
for i, temp_name in enumerate(temp_names, start=1):
    temp_path = os.path.join(folder, temp_name)
    # health_01.jpg, health_02.jpg ...
    new_name = f"festival_common_{i:02d}.jpg"
    new_path = os.path.join(folder, new_name)

    if os.path.exists(new_path):
        print(f"⚠ 目標檔名已存在，略過：{new_name}")
        continue

    os.rename(temp_path, new_path)
    print(f"{temp_name} -> {new_name}")

print("完成重新編號！")
