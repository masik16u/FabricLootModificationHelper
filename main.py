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

                result = "WeatherCheckLootCondition.create()"

                if 'thundering' in condition_object:

                    result += ".thundering(" + ("true" if condition_object['thundering'] else "false") + ")"

                if 'raining' in condition_object:

                    result += ".raining(" + ("true" if condition_object['raining'] else "false") + ")"

                return result

            # Value check
            if condition_type == "minecraft:value_check":

                return "ValueCheckLootCondition.builder(" + loot_number(condition_object['value']) + \
                    ", " + bounded_int_unary_operator(condition_object['range']) + ")"

            # Time check
            if condition_type == "minecraft:time_check":

                result = "TimeCheckLootCondition.create(" + \
                         bounded_int_unary_operator(condition_object['value']) + ")"

                if 'period' in condition_object:

                    result += ".period(" + str(condition_object['period']) + ")"

                return result

            # Table bonus
            if condition_type == "minecraft:table_bonus":

                result = "TableBonusLootCondition.builder(registries.getWrapperOrThrow(" \
                         "RegistryKeys.ENCHANTMENT).getOrThrow(RegistryKey.of(RegistryKeys.ENCHANTMENT, " \
                         "Identifier.of(\"" + condition_object['enchantment'] + "\"))"

                for chance in condition_object['chances']:

                    result += ", " + str(chance)

                result += "))"

                return result

            # Survives explosion
            if condition_type == "minecraft:survives_explosion":

                return "SurvivesExplosionLootCondition.builder()"

            # Reference
            if condition_type == "minecraft:reference":

                return "ReferenceLootCondition.builder(RegistryKey.of(RegistryKeys.PREDICATE, " \
                       "Identifier.of(\"" + condition_object['name'] + "\")))"

            # Random chance with enchanted bonus
            if condition_type == "minecraft:random_chance_with_enchanted_bonus":

                return "new RandomChanceWithEnchantedBonusLootCondition(" + \
                       str(condition_object['unenchanted_chance']) + "F, " + \
                       str(enchantment_level_value(condition_object['enchanted_chance'])) + ", " \
                       "registries.getWrapperOrThrow(RegistryKeys.ENCHANTMENT).getOrThrow(RegistryKey.of(" \
                       "RegistryKeys.ENCHANTMENT, Identifier.of(\"" + condition_object['enchantment'] + "\"))))"

            # Random chance
            if condition_type == "minecraft:random_chance":

                return "RandomChanceLootCondition.builder(" + \
                       loot_number(condition_object['chance']) + ")"

            # Match tool
            if condition_type == "minecraft:match_tool":

                result = "MatchToolLootCondition.builder(ItemPredicate.Builder.create()"

                predicate = condition_object['predicate']

                if 'items' in predicate:

                    result += ".tag(TagKey.of(RegistryKeys.ITEM, Identifier.of(\"" + \
                              str(predicate['items']).replace('#', '') + "\")))"

                if 'count' in predicate:

                    if isinstance(predicate['count'], int):

                        result += ".count(NumberRange.IntRange.exactly(" + \
                                  str(predicate['count']) + "))"

                    else:

                        result += ".count(NumberRange.IntRange.between(" + \
                                  str(predicate['count']['min']) + ", " + \
                                  str(predicate['count']['max']) + "))"

                # No components and predicates support

                result += ")"

                return result

            # Location check
            if condition_type == "minecraft:location_check":

                result = "LocationCheckLootCondition.builder(LocationPredicate.Builder.create()"

                predicate = condition_object['predicate']

                # Position predicate
                if 'position' in predicate:

                    if 'x' in predicate['position']:

                        x = predicate['position']['x']

                        if isinstance(x, Number):

                            result += ".x(NumberRange.DoubleRange.exactly(" + \
                                      str(x) + "F))"

                        else:

                            result += ".x(NumberRange.DoubleRange.between(" + \
                                      str(x['min']) + "F, " + \
                                      str(x['max']) + "F))"

                    if 'y' in predicate['position']:

                        y = predicate['position']['y']

                        if isinstance(y, Number):

                            result += ".y(NumberRange.DoubleRange.exactly(" + \
                                      str(y) + "F))"

                        else:

                            result += ".y(NumberRange.DoubleRange.between(" + \
                                      str(y['min']) + "F, " + \
                                      str(y['max']) + "F))"

                    if 'z' in predicate['position']:

                        z = predicate['position']['z']

                        if isinstance(z, Number):

                            result += ".z(NumberRange.DoubleRange.exactly(" + \
                                      str(z) + "F))"

                        else:

                            result += ".z(NumberRange.DoubleRange.between(" + \
                                      str(z['min']) + "F, " + \
                                      str(z['max']) + "F))"

                # Biomes predicate
                if 'biomes' in predicate:

                    # No biome tags support

                    result += ".biome(RegistryEntryList.of(registries.getWrapperOrThrow(" \
                              "RegistryKeys.BIOME).getOrThrow(RegistryKey.of(RegistryKeys.BIOME, Identifier.of(\"" + \
                              predicate['biomes'] + "\")))))"

                # Structure predicate
                if 'structures' in predicate:

                    result += ".structure(RegistryEntryList.of(registries.getWrapperOrThrow(" \
                              "RegistryKeys.STRUCTURE).getOrThrow(RegistryKey.of(RegistryKeys.STRUCTURE, " \
                              "Identifier.of(\"" + predicate['structures'] + "\")))))"

                # Dimension predicate
                if 'dimension' in predicate:

                    result += ".dimension(RegistryKey.of(RegistryKeys.WORLD, Identifier.of(\"" + \
                              predicate['dimension'] + "\")))"

                # Light predicate
                if 'light' in predicate:

                    if 'light' in predicate['light']:

                        result += ".light(LightPredicate.Builder.create().light(NumberRange.IntRange.exactly(" + \
                                  str(predicate['light']['light']) + ")))"

                    else:

                        result += ".light(LightPredicate.Builder.create().light(NumberRange.IntRange.between(" + \
                                  str(predicate['light']['min']) + ", " + \
                                  str(predicate['light']['max']) + ")))"

                # Smokey predicate
                if 'smokey' in predicate:

                    result += ".smokey(" + ("true" if predicate['smokey'] else "false") + ")"

                # Can see sky predicate
                if 'can_see_sky' in predicate:

                    result += ".canSeeSky(" + ("true" if predicate['can_see_sky'] else "false") + ")"

                # Block predicate
                if 'block' in predicate:

                    result += ".block(BlockPredicate.Builder.create()"

                    if 'blocks' in predicate['block']:

                        blocks = predicate['block']['blocks']

                        if '#' not in str(blocks):

                            result += ".blocks(Registries.BLOCK.get(Identifier.of(\"" + blocks + "\"))))"

                        else:

                            result += ".tag(TagKey.of(RegistryKeys.BLOCK, Identifier.of(\"" + \
                                      str(blocks).replace('#', '') + "\"))))"

                    # No state support

                # Fluid predicate
                if 'fluid' in predicate:

                    result += ".fluid(FluidPredicate.Builder.create()"

                    if 'fluids' in predicate['fluid']:

                        fluids = predicate['fluid']['fluids']

                        result += ".fluid(Registries.FLUID.get(Identifier.of(\"" + fluids + "\"))))"

                        # No fluid tag support

                    # No state support

                # Block offset
                if 'offsetX' in condition_object or 'offsetY' in condition_object or 'offsetZ' in condition_object:

                    result += ", new BlockPos("

                    if 'offsetX' in condition_object:

                        result += str(condition_object['offsetX']) + ", "

                    else:

                        result += "0, "

                    if 'offsetY' in condition_object:

                        result += str(condition_object['offsetY']) + ", "

                    else:

                        result += "0, "

                    if 'offsetZ' in condition_object:

                        result += str(condition_object['offsetZ']) + ")"

                    else:

                        result += "0)"

                result += ")"

                return result

            # Killed by player
            if condition_type == "minecraft:killed_by_player":

                result = "KilledByPlayerLootCondition.builder()"

                if 'inverse' in condition_object:

                    if condition_object['inverse']:

                        result += ".invert()"

                return result

            # Inverted
            if condition_type == "minecraft:inverted":

                return "InvertedLootCondition.builder(" + loot_condition(condition_object['term']) + ")"

            # Entity scores
            # if condition_type == "minecraft:entity_scores":
            #
            #     result = "EntityScoresLootCondition.create(LootContext.EntityTarget." + \
            #              str(condition_object['entity']).upper() + ")"
            #
            #     for score in condition_object['scores'].items():
            #
            #         result += ".score(\"" + score[0] + "\", " + str(isinstance(score, tuple)) + ")"
            #
            #     return result

            # Entity properties
            if condition_type == "minecraft:entity_properties":

                return ""

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

                print("\t\t.conditionally(" + loot_condition(condition) + ")")

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
