import json
from enum import IntEnum


def loot_table_json_to_java(path: str, event: int):
    """
    Reads 'loot_table.json' file and writes a Java code for Minecraft Fabric 1.21 in console

    :param path: data pack path to the desired loot table, e.g. 'gameplay/sniffer_digging'
    :param event: LootTableEvent.MODIFY / LootTableEvent.REPLACE

    LootTableEvent.MODIFY - add all pools from 'loot_table.json' to chosen table
    e.g. You modify 'blocks/stone' loot table, stone will drop vanilla item AND your item/items

    LootTableEvent.REPLACE - take all entries from the first pool in 'loot_table.json'
    and put them into the first pool of chosen table
    (use REPLACE to modify loot tables like fishing or archaeology, that have only one pool)
    e.g. You modify 'blocks/stone' loot table, stone will drop ONLY vanilla item OR your item

    P.S. to use REPLACE event you need to widen access for LootTable.pools field using accesswidener:
    'accessible field net/minecraft/loot/LootTable pools Ljava/util/List;'
    and you need to create a 'mergePools' method:
    'private static LootTable mergePools(LootTable original, LootPool lootPool) {
        LootPool pool = LootPool.builder().with(original.pools.get(0).entries).with(lootPool.entries).build();
        return LootTable.builder().pools(List.of(pool)).build();
    }'

    :return:
    """

    def build_pool(pool):

        # Get matching LootNumberProvider
        def loot_number(number_object):

            # If it is just a number
            if isinstance(number_object, int):

                return "ConstantLootNumberProvider.create(" + str(number_object) + "F)"

            # If it has certain type
            elif 'type' in number_object:

                roll_type = number_object['type']

                # Constant+
                if roll_type == "minecraft:constant":

                    return "ConstantLootNumberProvider.create(" + number_object['value'] + "F)"

                # Uniform+
                elif roll_type == "minecraft:uniform":

                    return "new UniformLootNumberProvider(" + loot_number(number_object['min']) + ", " + \
                           loot_number(number_object['max']) + ")"

                # Binomial
                elif roll_type == "minecraft:binomial":

                    return "new BinomialLootNumberProvider(" + loot_number(number_object['n']) + ", " + \
                           loot_number(number_object['p']) + ")"

                # Score
                elif roll_type == "minecraft:score":

                    result = "ScoreLootNumberProvider.create(LootContext.EntityTarget."

                    # Target
                    if isinstance(number_object['target'], str):

                        result += str(number_object['target']).upper()

                    else:

                        if number_object['target']['type'] == "minecraft:fixed":

                            result += "fromString(\"" + number_object['target']['name'] + "\")"

                        else:

                            result += str(number_object['target']['target']).upper()

                    # Score
                    result += ", \"" + number_object['score'] + "\""

                    # Scale
                    if 'scale' in number_object:

                        result += ", " + str(number_object['scale']) + "F"

                    result += ")"

                    return result

                # Storage
                elif roll_type == "minecraft:binomial":

                    return "new BinomialLootNumberProvider(" + loot_number(number_object['n']) + ", " + \
                           loot_number(number_object['p']) + ")"

        # Start building
        print("\tLootPool.Builder lootPool = LootPool.builder()")

        if 'rolls' in pool:

            rolls = pool['rolls']

            print("\t\t.rolls(" + loot_number(rolls) + ")")

        # End building for MODIFY event
        if event == 0:
            print("\ttableBuilder.pool(lootPool);\n")

        # End building for REPLACE event
        elif event == 1:
            print("\treturn mergePools(original, lootPool.build());\n")

    # Getting text from 'loot_table.json' file
    with open('loot_table.json', 'r') as file:
        data = file.read()

    # Loading JSON data from file to Python object
    table = json.loads(data)

    # Write Java code in console
    # Opening string
    print("if (key == RegistryKey.of(RegistryKeys.LOOT_TABLE, Identifier.of(\"" + path + "\"))) {\n")

    # Build all pools if event == MODIFY
    if event == 0:

        for modify_pool in table['pools']:
            build_pool(modify_pool)

    # Build first pool if event == REPLACE
    elif event == 1:

        build_pool(table['pools'][0])

    # Closing string
    print("}")

    # print(table['pools'][0]['entries'][0]['conditions'])


class LootTableEvent(IntEnum):
    MODIFY = 0
    REPLACE = 1


loot_table_json_to_java("gameplay/sniffer_digging", LootTableEvent.MODIFY)
