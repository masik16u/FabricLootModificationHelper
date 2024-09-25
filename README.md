The goal of this project is to help Fabric modders convert loot tables from JSON format to Java code:

Go from this:

{
  "pools": [
    {
      "rolls": 1,
      "entries": [
        {
          "type": "minecraft:item",
          "name": "minecraft:carrot"
        }
      ],
      "conditions": [
        {
          "condition": "minecraft:random_chance",
          "chance": 0.5
        }
      ]
    }
  ]
}

To this:

if (key == RegistryKey.of(RegistryKeys.LOOT_TABLE, Identifier.of("chests/igloo_chest"))) {

    LootPool.Builder lootPool = LootPool.builder()
            .with(ItemEntry.builder(Registries.ITEM.get(Identifier.of("minecraft:carrot"))))
            .conditionally(RandomChanceLootCondition.builder(0.5f));

    tableBuilder.pool(lootPool);

}
