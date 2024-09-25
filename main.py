import json
from numbers import Number
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

    IMPORTANT! to use REPLACE event you need to widen access for LootTable.pools field using accesswidener:
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
            """
            Helper method, converts object to EnchantmentLevelLootNumberProvider
            """

            # Just a number
            if isinstance(amount_object, Number):

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
            """
            Helper method, converts object to LootNumberProvider
            """

            # If it is just a number
            if isinstance(number_object, Number):

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

        # Get BoundedIntUnaryOperator
        def bounded_int_unary_operator(value_object):
            """
            Helper method, converts object to BoundedIntUnaryOperator

            IMPORTANT!
            if you DON'T use exact number or constant for both min and max values for the value you need to add this to your accesswidener:
            'accessible method net/minecraft/loot/operator/BoundedIntUnaryOperator <init> (Lnet/minecraft/loot/provider/number/LootNumberProvider;Lnet/minecraft/loot/provider/number/LootNumberProvider;)V'
            """

            min_value = value_object.get('min')
            max_value = value_object.get('max')

            if isinstance(value_object, int):

                return "BoundedIntUnaryOperator.create(" + str(value_object) + ")"

            elif isinstance(min_value, int) and isinstance(max_value, int):

                return "BoundedIntUnaryOperator.create(" + str(min_value) + ", " + str(max_value) + ")"

            else:

                result = "new BoundedIntUnaryOperator("

                if 'min' in value_object:

                    result += loot_number(value_object['min'])

                else:

                    result += "null"

                result += ", "

                if 'max' in value_object:

                    result += loot_number(value_object['max'])

                else:

                    result += "null"

                result += ")"

                return result

        # Get matching LootCondition
        def loot_condition(condition_object):

            condition_type = condition_object['condition']

            # Weather check
            if condition_type == "minecraft:weather_check":

                result = ".conditionally(WeatherCheckLootCondition.create()"

                if 'thundering' in condition_object:

                    result += ".thundering(" + ("true" if condition_object['thundering'] else "false") + ")"

                if 'raining' in condition_object:

                    result += ".raining(" + ("true" if condition_object['raining'] else "false") + ")"

                result += ")"

                return result

            # Value check
            if condition_type == "minecraft:value_check":

                return ".conditionally(ValueCheckLootCondition.builder(" + loot_number(condition_object['value']) + \
                    ", " + bounded_int_unary_operator(condition_object['range']) + "))"

            # Time check
            if condition_type == "minecraft:time_check":

                result = ".conditionally(TimeCheckLootCondition.create(" + \
                         bounded_int_unary_operator(condition_object['value']) + ")"

                if 'period' in condition_object:

                    result += ".period(" + str(condition_object['period']) + ")"

                result += ")"

                return result

            # Table bonus
            if condition_type == "minecraft:table_bonus":

                result = ".conditionally(TableBonusLootCondition.builder(registries.getWrapperOrThrow(" \
                         "RegistryKeys.ENCHANTMENT).getOrThrow(RegistryKey.of(RegistryKeys.ENCHANTMENT, " \
                         "Identifier.of(\"" + condition_object['enchantment'] + "\")))"

                for chance in condition_object['chances']:

                    result += ", " + str(chance)

                result += "))"

                return result

            # Survives explosion
            if condition_type == "minecraft:survives_explosion":

                return ".conditionally(SurvivesExplosionLootCondition.builder())"

            # Reference
            if condition_type == "minecraft:reference":

                return ".conditionally(ReferenceLootCondition.builder(RegistryKey.of(RegistryKeys.PREDICATE, " \
                       "Identifier.of(\"" + condition_object['name'] + "\"))))"

            # Random chance with enchanted bonus
            if condition_type == "minecraft:random_chance_with_enchanted_bonus":

                return ".conditionally(new RandomChanceWithEnchantedBonusLootCondition(" + \
                       str(condition_object['unenchanted_chance']) + "F, " + \
                       str(enchantment_level_value(condition_object['enchanted_chance'])) + ", " \
                       "registries.getWrapperOrThrow(RegistryKeys.ENCHANTMENT).getOrThrow(RegistryKey.of(" \
                       "RegistryKeys.ENCHANTMENT, Identifier.of(\"" + condition_object['enchantment'] + "\")))))"

            # Random chance
            if condition_type == "minecraft:random_chance":

                return ".conditionally(RandomChanceLootCondition.builder(" + \
                       loot_number(condition_object['chance']) + "))"

            # Match tool
            if condition_type == "minecraft:match_tool":

                result = ".conditionally(MatchToolLootCondition.builder(ItemPredicate.Builder.create()"

                if 'items' in condition_object['predicate']:

                    result += ".tag(TagKey.of(RegistryKeys.ITEM, Identifier.of(\"" + \
                              condition_object['predicate']['items'][1:] + "\")))"

                if 'count' in condition_object['predicate']:

                    if isinstance(condition_object['predicate']['count'], int):

                        result += ".count(NumberRange.IntRange.exactly(" + \
                                  str(condition_object['predicate']['count']) + "))"

                    else:

                        result += ".count(NumberRange.IntRange.between(" + \
                                  str(condition_object['predicate']['count']['min']) + ", " + \
                                  str(condition_object['predicate']['count']['max']) + "))"

                # No components and predicates support

                result += "))"

                return result

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

        # Entries

        # POOL Conditions
        if 'conditions' in pool:

            conditions = pool['conditions']

            for condition in conditions:

                print("\t\t" + loot_condition(condition))

        # POOL Functions

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
