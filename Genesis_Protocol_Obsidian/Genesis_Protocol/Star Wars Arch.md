

```py
from diagrams import Diagram
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL

with Diagram("Star Wars Architecture", show=False, filename="star_wars_arch"):
	Server("Game Master AI") >> PostgreSQL("Rules Database")
```



```d2
Jedi: {
  # Fields
  name: string
  midichlorianCount: int
  
  # Methods
  useForce()
  igniteSaber()
}
Lightsaber: {color: string}

Jedi -> Lightsaber: owns
```
