# Phoenix Real-World Evidence Persistence & Clean Repository Fix v1.0

De PAT toonde dat geldige Suriname real-world evidence onder
`inputs/**/acquired/<project_id>` werd opgeslagen en daardoor de Git working tree
vuil maakte.

Voortaan wordt dynamische acquired evidence projectspecifiek opgeslagen onder:

`projects/runtime/<project_id>/sources/<category>/`

De Local Cost-, Local Material- en Structural Action/Load-readers lezen de
huidige projectsources rechtstreeks. Daardoor kan evidence van project A niet
stilzwijgend als projectspecifieke bron voor project B worden gebruikt.

De installer migreert bestaande PAT-evidence met SHA256-registratie en verwijdert
de oude runtimekopieën pas na succesvolle kopie/controle.

Productievrijgave en alle engineering gates blijven ongewijzigd en LOCKED.
