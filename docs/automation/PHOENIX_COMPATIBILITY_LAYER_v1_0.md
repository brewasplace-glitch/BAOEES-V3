# Phoenix Compatibility Layer v1.0

De bestaande Updater v1.1 PackageBuilder blijft beschikbaar via:

```python
from phoenix.updater.package_builder import PackageBuilder
```

De Release Manager gebruikt voortaan afzonderlijk:

```python
from phoenix.updater.release_package_builder import ReleasePackageBuilder
```

Hierdoor blijven legacy-argumenten zoals `update_id` werken zonder de nieuwe
releasearchitectuur te beperken.

UTF-8 tekstbestanden worden in release-ZIP's naar LF genormaliseerd. Binaire
bestanden blijven byte voor byte ongewijzigd.