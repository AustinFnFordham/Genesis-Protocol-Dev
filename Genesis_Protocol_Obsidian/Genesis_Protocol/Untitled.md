
```python
import sys
print(f"Hello Austin! Running Python version: {sys.version}")

# Calculate something simple
x = 10
y = 50
print(f"The calculation result is: {x * y}") 
```

```python
print("It works now!")
```

```python
# You must have the 'Execute Code' plugin enabled
from diagrams import Diagram
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL

# This generates 'star_wars_arch.png' in your folder
with Diagram("Star Wars Architecture", show=False, filename="star_wars_arch"):
    Server("Game Master AI") >> PostgreSQL("Rules Database")
```
