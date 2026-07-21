import yaml

file_path = r"e:\StarWars\SW5e_Data_Hub\SW5e_Data_Hub\data\species\wookiee.yml"

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    print(f"Keys in {file_path}:")
    for key in data.keys():
        print(f"- {key}")
        
    if 'romance_engine' in data:
        print("\nRomance Engine FOUND")
    else:
        print("\nRomance Engine MISSING")
        
    if 'companion_engine' in data:
        print("Companion Engine FOUND")
    else:
        print("Companion Engine MISSING")

except Exception as e:
    print(f"Error loading YAML: {e}")
