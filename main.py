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

        # Get amount value for EnchantmentLevelLootNumberProvider
        def enchantment_level_value(amount_object):

            # Just a number
            if isinstance(amount_object, int):

                return "new EnchantmentLevelBasedValue.Constant(" + str(amount_object) + "F)"

            # Has type
            elif 'type' in amount_object:

                amount_type = amount_object['type']

                # Constant+
                if amount_type == "minecraft:constant":

                    return "new EnchantmentLevelBasedValue.Constant(" + amount_object['value'] + "F)"

                # Clamped
                elif amount_type == "minecraft:clamped":

                    return "new EnchantmentLevelBasedValue.Clamped(" + \
                           enchantment_level_value(amount_object['value']) + ", " + str(amount_object['min']) + \
                           "F, " + str(amount_object['max']) + "F)"

                # Fraction
                elif amount_type == "minecraft:fraction":

                    return "new EnchantmentLevelBasedValue.Fraction(" + \
                           enchantment_level_value(amount_object['numerator']) + ", " + \
                           enchantment_level_value(amount_object['denominator']) + ")"

                # Levels squared
                elif amount_type == "minecraft:levels_squared":

                    return "new EnchantmentLevelBasedValue.LevelsSquared(" + str(amount_object['added']) + "F)"

                # Linear
                elif amount_type == "minecraft:linear":

                    return "new EnchantmentLevelBasedValue.Linear(" + str(amount_object['base']) + "F, " + \
                           str(amount_object['per_level_above_first']) + "F)"

                # Lookup
                elif amount_type == "minecraft:lookup":

                    result = "new EnchantmentLevelBasedValue.Lookup(Arrays.asList("

                    for value in amount_object['values']:

                        result += str(value) + "F, "

                    result = result[:-2]

                    result += "), " + enchantment_level_value(amount_object['fallback']) + ")"

                    return result

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

                # Storage - needs try catch, maybe next time

                # Enchantment level
                elif roll_type == "minecraft:enchantment_level":

                    return "new EnchantmentLevelLootNumberProvider(" + \
                           enchantment_level_value(number_object['amount']) + ")"

            # Uniform type without 'type' field
            elif 'min' in number_object and 'max' in number_object:

                return "new UniformLootNumberProvider(" + loot_number(number_object['min']) + ", " + \
                       loot_number(number_object['max']) + ")"

        # Get matching LootCondition
        def loot_condition(condition_object):

            print()

        # Get matching LootFunction
        def loot_function(function_object):

            print()

        # --- Start building ---
        print("\tLootPool.Builder lootPool = LootPool.builder()")

        # Rolls
        if 'rolls' in pool:

            rolls = pool['rolls']

            print("\t\t.rolls(" + loot_number(rolls) + ")")

        # Bonus rolls
        if 'bonus_rolls' in pool:

            rolls = pool['bonus_rolls']

            print("\t\t.bonusRolls(" + loot_number(rolls) + ")")

        # --- End building for MODIFY event ---
        if event == 0:
            print("\ttableBuilder.pool(lootPool);\n")

        # --- End building for REPLACE event ---
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
