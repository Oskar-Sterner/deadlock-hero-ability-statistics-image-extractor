from deadlock_hero_ability_statistics_image_extractor.item_catalog import (
    TAB_CLICK_POSITIONS_1440P,
    build_item_tooltip_tabs,
)


def test_item_catalog_has_three_tabs_with_expected_click_positions():
    tabs = build_item_tooltip_tabs()

    assert len(tabs) == 3
    assert tabs[0].tab_id == 1
    assert tabs[1].tab_id == 2
    assert tabs[2].tab_id == 3

    for tab in tabs:
        assert tab.tab_click_position_1440p == TAB_CLICK_POSITIONS_1440P[tab.tab_id]


def test_item_catalog_sizes_and_known_samples_match_expected():
    tabs = build_item_tooltip_tabs()

    assert len(tabs[0].items) == 53
    assert len(tabs[1].items) == 52
    assert len(tabs[2].items) == 49

    assert tabs[0].items[0].item_id == 1342610602
    assert tabs[0].items[0].item_name == "Close Quarters"
    assert tabs[0].items[0].hover_position_1440p == (960, 363)

    assert tabs[2].items[-1].item_id == 1152158042
    assert tabs[2].items[-1].item_name == "Vortex Web"


def test_item_catalog_coordinate_inheritance_rules_for_tab2_and_tab3():
    tabs = build_item_tooltip_tabs()
    tab1 = tabs[0].items
    tab2 = tabs[1].items
    tab3 = tabs[2].items

    assert tab2[0].hover_position_1440p == tab1[0].hover_position_1440p
    assert tab2[20].hover_position_1440p == tab1[20].hover_position_1440p

    assert tab3[0].hover_position_1440p == tab1[0].hover_position_1440p
    assert tab3[19].hover_position_1440p == tab2[19].hover_position_1440p
