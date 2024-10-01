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

        # Get DoubleRange
        def double_range(value_object):
            """
            Helper method, converts object to DoubleRange exactly or between
            """

            if isinstance(value_object, Number):

                return "NumberRange.DoubleRange.exactly(" + str(value_object) + "F)"

            else:

                return "NumberRange.DoubleRange.between(" + \
                       str(value_object['min']) + "F, " + str(value_object['max']) + "F)"

        # Get DoubleRange if value exists ANY if doesn't
        def double_range_or_any(obj, value_name):
            """
            Helper method, returns DoubleRange if value exists, otherwise returns DoubleRange.ANY
            """

            if value_name in obj:

                return double_range(obj[value_name])

            else:

                return "NumberRange.DoubleRange.ANY"

        # Get IntRange
        def int_range(value_object):
            """
            Helper method, converts object to IntRange exactly or between
            """

            if isinstance(value_object, int):

                return "NumberRange.IntRange.exactly(" + str(value_object) + ")"

            else:

                return "NumberRange.IntRange.between(" + \
                       str(value_object['min']) + ", " + str(value_object['max']) + ")"

        # Get IntRange if value exists ANY if doesn't
        def int_range_or_any(obj, value_name):
            """
            Helper method, returns IntRange if value exists, otherwise returns DoubleRange.ANY
            """

            if value_name in obj:

                return int_range(obj[value_name])

            else:

                return "NumberRange.IntRange.ANY"

        # Get location predicate
        def location_predicate(predicate_object, number_of_tabs):
            """
            Helper method, converts object to LocationPredicate
            """

            result = "LocationPredicate.Builder.create()"

            # Position predicate
            if 'position' in predicate_object:

                if 'x' in predicate_object['position']:

                    result += "\n" + tabs(number_of_tabs + 1) + ".x(" + \
                              double_range(predicate_object['position']['x']) + ")"

                if 'y' in predicate_object['position']:

                    result += "\n" + tabs(number_of_tabs + 1) + ".y(" + \
                              double_range(predicate_object['position']['y']) + ")"

                if 'z' in predicate_object['position']:

                    result += "\n" + tabs(number_of_tabs + 1) + ".z(" + \
                              double_range(predicate_object['position']['z']) + ")"

            # Biomes predicate
            if 'biomes' in predicate_object:
                # No biome tags support

                result += "\n" + tabs(number_of_tabs + 1) + ".biome(RegistryEntryList.of("

                if isinstance(predicate_object['biomes'], str):

                    result += "\n" + tabs(number_of_tabs + 2) + "registries.getWrapperOrThrow(" \
                              "RegistryKeys.BIOME).getOrThrow(RegistryKey.of(" \
                              "RegistryKeys.BIOME, Identifier.of(\"" + predicate_object['biomes'] + "\")))"

                else:

                    for biome in predicate_object['biomes']:

                        result += "\n" + tabs(number_of_tabs + 2) + "registries.getWrapperOrThrow(" \
                                  "RegistryKeys.BIOME).getOrThrow(RegistryKey.of(" \
                                  "RegistryKeys.BIOME, Identifier.of(\"" + biome + "\"))), "

                    result = result[:-2]

                result += "))"

            # Structure predicate
            if 'structures' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".structure(RegistryEntryList.of("

                if isinstance(predicate_object['structures'], str):

                    result += "\n" + tabs(number_of_tabs + 2) + "registries.getWrapperOrThrow(" \
                              "RegistryKeys.STRUCTURE).getOrThrow(RegistryKey.of(" \
                              "RegistryKeys.STRUCTURE, Identifier.of(\"" + predicate_object['biomes'] + "\")))"

                else:

                    for structure in predicate_object['structures']:

                        result += "\n" + tabs(number_of_tabs + 2) + "registries.getWrapperOrThrow(" \
                                  "RegistryKeys.STRUCTURE).getOrThrow(RegistryKey.of(" \
                                  "RegistryKeys.STRUCTURE, Identifier.of(\"" + structure + "\"))), "

                    result = result[:-2]

                result += "))"

            # Dimension predicate
            if 'dimension' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".dimension(RegistryKey.of(" \
                          "RegistryKeys.WORLD, Identifier.of(\"" + predicate_object['dimension'] + "\")))"

            # Light predicate
            if 'light' in predicate_object:

                if 'light' in predicate_object['light']:

                    result += "\n" + tabs(number_of_tabs + 1) + ".light(LightPredicate.Builder.create().light(" \
                              "NumberRange.IntRange.exactly(" + \
                              str(predicate_object['light']['light']) + ")))"

                else:

                    result += "\n" + tabs(number_of_tabs + 1) + ".light(LightPredicate.Builder.create().light(" \
                              "NumberRange.IntRange.between(" + \
                              str(predicate_object['light']['min']) + ", " + \
                              str(predicate_object['light']['max']) + ")))"

            # Smokey predicate
            if 'smokey' in predicate_object:
                result += "\n" + tabs(number_of_tabs + 1) + ".smokey(" + \
                          ("true" if predicate_object['smokey'] else "false") + ")"

            # Can see sky predicate
            if 'can_see_sky' in predicate_object:
                result += "\n" + tabs(number_of_tabs + 1) + ".canSeeSky(" + \
                          ("true" if predicate_object['can_see_sky'] else "false") + ")"

            # Block predicate
            if 'block' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".block(BlockPredicate.Builder.create()"

                if 'blocks' in predicate_object['block']:

                    blocks = predicate_object['block']['blocks']

                    if '#' not in str(blocks):

                        result += "\n" + tabs(number_of_tabs + 2) + ".blocks(Registries.BLOCK.get(Identifier.of(\"" + \
                                  blocks + "\"))))"

                    else:

                        result += "\n" + tabs(number_of_tabs + 2) + ".tag(TagKey.of(" \
                                  "RegistryKeys.BLOCK, Identifier.of(\"" + \
                                  str(blocks).replace('#', '') + "\"))))"

                # No state support

            # Fluid predicate
            if 'fluid' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".fluid(FluidPredicate.Builder.create()"

                if 'fluids' in predicate_object['fluid']:

                    fluids = predicate_object['fluid']['fluids']

                    if '#' not in str(fluids):

                        result += "\n" + tabs(number_of_tabs + 2) + ".fluid(Registries.FLUID.get(" \
                                  "Identifier.of(\"" + fluids + "\"))))"

                    else:

                        result += "\n" + tabs(number_of_tabs + 2) + ".tag(Registries.FLUID.getOrCreateEntryList(" \
                                  "TagKey.of(RegistryKeys.FLUID, " \
                                  "Identifier.of(\"" + str(fluids).replace('#', '') + "\")))) "

                # No state support

            return result

        # Get entity predicate
        def entity_predicate(predicate_object, number_of_tabs):
            """
            Helper method, converts object to EntityPredicate
            """

            result = "EntityPredicate.Builder.create()"

            # Entity type predicate
            if 'type' in predicate_object:

                if '#' not in str(predicate_object['type']):

                    result += "\n" + tabs(number_of_tabs + 1) + ".type(EntityTypePredicate.create("\
                              "Registries.ENTITY_TYPE.get(Identifier.of(\"" + \
                              predicate_object['type'] + "\"))))"

                else:

                    result += "\n" + tabs(number_of_tabs + 1) + ".type(EntityTypePredicate.create(TagKey.of(" \
                              "RegistryKeys.ENTITY_TYPE, " \
                              "Identifier.of(\"" + str(predicate_object['type']).replace('#', '') + "\")))) "

            # No support for type specific

            # No support for nbt

            # Team predicate
            if 'team' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".team(\"" + predicate_object['team'] + "\")"

            # Location predicate
            if 'location' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".location(" + \
                          location_predicate(predicate_object['location'], number_of_tabs + 1) + ")"

            # Movement predicate
            if 'movement' in predicate_object:

                movement = predicate_object['movement']

                result += "\n" + tabs(number_of_tabs + 1) + ".movement(new MovementPredicate("

                result += double_range_or_any(movement, 'x') + ", " + \
                          double_range_or_any(movement, 'y') + ", " + \
                          double_range_or_any(movement, 'z') + ", " + \
                          double_range_or_any(movement, 'speed') + ", " + \
                          double_range_or_any(movement, 'horizontal_speed') + ", " + \
                          double_range_or_any(movement, 'vertical_speed') + ", " + \
                          double_range_or_any(movement, 'fall_speed') + "))"

            # Movement affected by predicate
            if 'movement_affected_by' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".movementAffectedBy(" + \
                          location_predicate(predicate_object['movement_affected_by'], number_of_tabs + 1) + ")"

            # Stepping on predicate
            if 'stepping_on' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".steppingOn(" + \
                          location_predicate(predicate_object['stepping_on'], number_of_tabs + 1) + ")"

            # Distance predicate
            if 'distance' in predicate_object:
                distance = predicate_object['distance']

                result += "\n" + tabs(number_of_tabs + 1) + ".distance(new DistancePredicate("

                result += double_range_or_any(distance, 'x') + ", " + \
                          double_range_or_any(distance, 'y') + ", " + \
                          double_range_or_any(distance, 'z') + ", " + \
                          double_range_or_any(distance, 'horizontal') + ", " + \
                          double_range_or_any(distance, 'absolute') + "))"

            # Flags predicate
            if 'flags' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".flags(EntityFlagsPredicate.Builder.create()"

                flags = predicate_object['flags']

                if 'is_on_ground' in flags:

                    result += "\n" + tabs(number_of_tabs + 2) + ".onGround(" + \
                              ("true" if flags['is_on_ground'] else "false") + ")"

                if 'is_on_fire' in flags:

                    result += "\n" + tabs(number_of_tabs + 2) + ".onFire(" + \
                              ("true" if flags['is_on_fire'] else "false") + ")"

                if 'is_sneaking' in flags:

                    result += "\n" + tabs(number_of_tabs + 2) + ".sneaking(" + \
                              ("true" if flags['is_sneaking'] else "false") + ")"

                if 'is_sprinting' in flags:

                    result += "\n" + tabs(number_of_tabs + 2) + ".sprinting(" + \
                              ("true" if flags['is_sprinting'] else "false") + ")"

                if 'is_swimming' in flags:

                    result += "\n" + tabs(number_of_tabs + 2) + ".swimming(" + \
                              ("true" if flags['is_swimming'] else "false") + ")"

                if 'is_flying' in flags:

                    result += "\n" + tabs(number_of_tabs + 2) + ".flying(" + \
                              ("true" if flags['is_flying'] else "false") + ")"

                if 'is_baby' in flags:

                    result += "\n" + tabs(number_of_tabs + 2) + ".isBaby(" + \
                              ("true" if flags['is_baby'] else "false") + ")"

                result += ")"

            # Equipment predicate
            if 'equipment' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".equipment(EntityEquipmentPredicate.Builder.create()"

                equipment = predicate_object['equipment']

                if 'mainhand' in equipment:

                    result += "\n" + tabs(number_of_tabs + 2) + ".mainhand(" + \
                              item_predicate(equipment['mainhand'], number_of_tabs + 2) + ")"

                if 'offhand' in equipment:

                    result += "\n" + tabs(number_of_tabs + 2) + ".offhand(" + \
                              item_predicate(equipment['offhand'], number_of_tabs + 2) + ")"

                if 'head' in equipment:

                    result += "\n" + tabs(number_of_tabs + 2) + ".head(" + \
                              item_predicate(equipment['head'], number_of_tabs + 2) + ")"

                if 'chest' in equipment:

                    result += "\n" + tabs(number_of_tabs + 2) + ".chest(" + \
                              item_predicate(equipment['chest'], number_of_tabs + 2) + ")"

                if 'legs' in equipment:

                    result += "\n" + tabs(number_of_tabs + 2) + ".legs(" + \
                              item_predicate(equipment['legs'], number_of_tabs + 2) + ")"

                if 'feet' in equipment:

                    result += "\n" + tabs(number_of_tabs + 2) + ".feet(" + \
                              item_predicate(equipment['feet'], number_of_tabs + 2) + ")"

                if 'body' in equipment:

                    result += "\n" + tabs(number_of_tabs + 2) + ".body(" + \
                              item_predicate(equipment['body'], number_of_tabs + 2) + ")"

                result += ")"

            # Periodic tick predicate
            if 'periodic_tick' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".periodicTick(" + \
                          str(predicate_object['periodic_tick']) + ")"

            # Vehicle predicate
            if 'vehicle' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".vehicle(" + \
                          entity_predicate(predicate_object['vehicle'], number_of_tabs + 1) + ")"

            # Passenger predicate
            if 'passenger' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".passenger(" + \
                          entity_predicate(predicate_object['passenger'], number_of_tabs + 1) + ")"

            # Targeted entity predicate
            if 'targeted_entity' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".targetedEntity(" + \
                          entity_predicate(predicate_object['targeted_entity'], number_of_tabs + 1) + ")"

            # Effects predicate
            if 'effects' in predicate_object:

                effects = predicate_object['effects']

                result += "\n" + tabs(number_of_tabs + 1) + ".effects(EntityEffectPredicate.Builder.create()"

                for effect_name, effect_data in effects.items():

                    result += "\n" + tabs(number_of_tabs + 2) + ".addEffect(registries.getWrapperOrThrow(" \
                              "RegistryKeys.STATUS_EFFECT).getOrThrow(" \
                              "RegistryKey.of(RegistryKeys.STATUS_EFFECT, Identifier.of(\"" + effect_name + "\"))), " \
                              "\n" + tabs(number_of_tabs + 3) + "new EntityEffectPredicate.EffectData("

                    result += int_range_or_any(effect_data, 'amplifier') + ", " + \
                              int_range_or_any(effect_data, 'duration') + ", "

                    if 'ambient' in effect_data:

                        result += ("Optional.of(true)" if effect_data['ambient'] else "Optional.of(false)") + ", "

                    else:

                        result += "Optional.empty(), "

                    if 'visible' in effect_data:

                        result += ("Optional.of(true)" if effect_data['visible'] else "Optional.of(false)")

                    else:

                        result += "Optional.empty()"

                    result += "))"

                result += ")"

            return result

        # Get item predicate
        def item_predicate(predicate_object, number_of_tabs):
            """
            Helper method, converts object to ItemPredicate
            """

            result = "ItemPredicate.Builder.create()"

            if 'items' in predicate_object:

                if '#' not in str(predicate_object['items']):

                    if isinstance(predicate_object['items'], str):

                        result += "\n" + tabs(number_of_tabs + 1) + ".items(Registries.ITEM.get(Identifier.of(\"" + \
                                  str(predicate_object['items']) + "\")))"

                    else:

                        result += "\n" + tabs(number_of_tabs + 1) + ".items("

                        for item in predicate_object['items']:

                            result += "\n" + tabs(number_of_tabs + 2) + "Registries.ITEM.get(Identifier.of(\"" + \
                                      str(item) + "\")), "

                        result = result[:-2] + ")"

                else:

                    result += "\n" + tabs(number_of_tabs + 1) + ".tag(TagKey.of(RegistryKeys.ITEM, Identifier.of(\"" + \
                              str(predicate_object['items']).replace('#', '') + "\")))"

            if 'count' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".count(" + int_range(predicate_object['count']) + ")"

            # No components and predicates support

            return result

        # Get damage source predicate
        def damage_source_predicate(predicate_object, number_of_tabs):
            """
            Helper method, converts object to DamageSourcePredicate
            """

            result = "DamageSourcePredicate.Builder.create()"

            if 'tags' in predicate_object:

                for tag in predicate_object['tags']:

                    result += "\n" + tabs(number_of_tabs + 1) + ".tag(TagPredicate." + \
                              ("expected" if tag['expected'] else "unexpected") + \
                              "(TagKey.of(RegistryKeys.DAMAGE_TYPE, Identifier.of(\"" + tag['id'] + "\"))))"

            if 'source_entity' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".sourceEntity(" + \
                          entity_predicate(predicate_object['source_entity'], number_of_tabs + 1) + ")"

            if 'direct_entity' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".directEntity(" + \
                          entity_predicate(predicate_object['direct_entity'], number_of_tabs + 1) + ")"

            if 'is_direct' in predicate_object:

                result += "\n" + tabs(number_of_tabs + 1) + ".isDirect(" + \
                          ("true" if predicate_object['is_direct'] else "false") + ")"

            return result

        # Tabs
        def tabs(number_of_tabs):

            return "\t" * number_of_tabs

        # Get matching LootCondition
        def loot_condition(condition_object, number_of_tabs):
            """
            Helper method, converts object to LootCondition
            """

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

                return "ValueCheckLootCondition.builder(" + "\n" + tabs(number_of_tabs + 1) + \
                       loot_number(condition_object['value']) + ", " + "\n" + tabs(number_of_tabs + 1) + \
                       bounded_int_unary_operator(condition_object['range']) + ")"

            # Time check
            if condition_type == "minecraft:time_check":

                result = "TimeCheckLootCondition.create(\n" + tabs(number_of_tabs + 1) + \
                         bounded_int_unary_operator(condition_object['value']) + ")"

                if 'period' in condition_object:

                    result += "\n" + tabs(number_of_tabs + 2) + ".period(" + str(condition_object['period']) + ")"

                return result

            # Table bonus
            if condition_type == "minecraft:table_bonus":

                result = "TableBonusLootCondition.builder(\n" + tabs(number_of_tabs + 1) + \
                         "registries.getWrapperOrThrow(" \
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
                       "\n" + tabs(number_of_tabs + 1) + str(condition_object['unenchanted_chance']) + "F, " + \
                       str(enchantment_level_value(condition_object['enchanted_chance'])) + ", " \
                       "\n" + tabs(number_of_tabs + 1) + "registries.getWrapperOrThrow(" \
                       "RegistryKeys.ENCHANTMENT).getOrThrow(RegistryKey.of(" \
                       "RegistryKeys.ENCHANTMENT, Identifier.of(\"" + condition_object['enchantment'] + "\"))))"

            # Random chance
            if condition_type == "minecraft:random_chance":

                return "RandomChanceLootCondition.builder(" + \
                       loot_number(condition_object['chance']) + ")"

            # Match tool
            if condition_type == "minecraft:match_tool":

                result = "MatchToolLootCondition.builder(\n" + tabs(number_of_tabs + 1) + \
                         item_predicate(condition_object['predicate'], number_of_tabs + 1) + ")"

                return result

            # Location check
            if condition_type == "minecraft:location_check":

                result = "LocationCheckLootCondition.builder(\n" + tabs(number_of_tabs + 1) + \
                         location_predicate(condition_object['predicate'], number_of_tabs + 1)

                # Block offset
                if 'offsetX' in condition_object or 'offsetY' in condition_object or 'offsetZ' in condition_object:

                    result += "\n" + tabs(number_of_tabs + 1) + ", new BlockPos("

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

                return "InvertedLootCondition.builder(\n" + tabs(number_of_tabs + 1) + \
                       loot_condition(condition_object['term'], number_of_tabs + 1) + ")"

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

                result = "EntityPropertiesLootCondition.builder(\n" + tabs(number_of_tabs + 1) + \
                         "LootContext.EntityTarget." + str(condition_object['entity']).upper() + ", \n" + \
                         tabs(number_of_tabs + 1) + \
                         entity_predicate(condition_object['predicate'], number_of_tabs + 1) + ")"

                return result

            # Enchantment active check
            if condition_type == "minecraft:enchantment_active_check":

                result = "EnchantmentActiveCheckLootCondition"

                if condition_object['active']:

                    result += ".requireActive()"

                else:

                    result += ".requireInactive()"

                return result

            # Damage source properties
            if condition_type == "minecraft:damage_source_properties":

                return "DamageSourcePropertiesLootCondition.builder(\n" + tabs(number_of_tabs + 1) + \
                       damage_source_predicate(condition_object['predicate'], number_of_tabs + 1) + ")"

            # Any of
            if condition_type == "minecraft:any_of":

                result = "AnyOfLootCondition.builder("

                for term in condition_object['terms']:

                    result += "\n" + tabs(number_of_tabs + 1) + loot_condition(term, number_of_tabs + 1) + ", "

                result = result[:-2] + ")"

                return result

            # All of
            if condition_type == "minecraft:all_of":

                result = "AllOfLootCondition.builder("

                for term in condition_object['terms']:

                    result += "\n" + tabs(number_of_tabs + 1) + loot_condition(term, number_of_tabs + 1) + ", "

                result = result[:-2] + ")"

                return result

        # Get matching LootFunction
        def loot_function(function_object):

            print()

            return ""

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

                print("\t\t.conditionally(" + loot_condition(condition, 2) + ")")

        # POOL Functions
        if 'functions' in pool:

            functions = pool['functions']

            for function in functions:

                print("\t\t.apply(" + loot_function(function) + ")")

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
