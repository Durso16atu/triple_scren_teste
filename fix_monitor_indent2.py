with open('src/monitor_realtime.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "grade_teorica = df_g.to_dict" in line:
        lines[i] = "                grade_teorica = df_g.to_dict(orient=\"records\")\n"

with open('src/monitor_realtime.py', 'w') as f:
    f.writelines(lines)
