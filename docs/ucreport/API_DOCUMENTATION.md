# War Server API Documentation

This document describes the six endpoints exposed by the `api` app. Every route is
registered in [api/urls.py](api/urls.py) and implemented in [api/views.py](api/views.py).
`track/urls.py` is empty and not wired in, so these six endpoints are the entire API surface.

- **Base URL (production):** `https://football-api-dot-football-344319.uc.r.appspot.com`
- **Base URL (local):** `http://127.0.0.1:8000`
- A ready-to-import Postman collection lives at [postman/war_server_all_routes.json](postman/war_server_all_routes.json).

---

## Conventions shared by every endpoint

All six endpoints are wrapped by the `validate_and_track` decorator and behave identically
with respect to method, auth, and request shape.

### Method & body
- **Method:** `POST` only.
- **Body:** raw JSON (`json.loads(request.body)`). A GET or a non-JSON body fails.
- **No trailing slash.** Routes are registered without one (e.g. `/api/get_masterlist`).
  Adding a trailing slash returns **404**.

### Authentication
- Send the API key in a request **header** named `key` (not in the body, not `Authorization`).
- The key must be one of the values in `valid_keys` in [api/views.py](api/views.py).
- Invalid/missing key → **403** `{"error": "access denied"}`.

### Required body field
- Every request body must contain a `college` field. Missing it → **400** `{"error": "No College"}`.
- `college` must match a row in the `Colleges` table (the `name` column). It selects the
  **package** that governs which players/states/permissions the caller may see.
- Passing an empty/`null` college grants **full access** to all states, max speed, and portal/archive
  (see `get_college_package` in [api/get_package_settings.py](api/get_package_settings.py)).

### Request parameters (in the JSON body)

| Field    | Type   | Default | Description |
|----------|--------|---------|-------------|
| `college`| string | —       | **Required.** Institution name; selects the access package. |
| `page`   | int    | `0`     | Zero-based page index. |
| `limit`  | int    | `1000`  | Page size. Only applied when `0 < limit < 1000`; otherwise 1000. |
| `filter` | object | none    | Django field lookups (see below). |
| `cols`   | array  | all     | Restrict returned columns, e.g. `["first", "last"]`. |

### Filtering (`filter`)
`filter` is passed straight into a Django `Q(**filter)`, so you use **Django field lookups**:
`field__lookup`. Supported lookups include:

`exact`, `iexact`, `contains`, `icontains`, `in`, `gt`, `gte`, `lt`, `lte`,
`startswith`, `istartswith`, `endswith`, `iendswith`, `range`, `isnull`, `regex`, `iregex`.

Examples:
```json
{ "first__icontains": "john" }
{ "height__gte": 72, "state__in": ["FL", "GA"] }
{ "class_field": 2026 }
```

### Response shape
```json
{
  "list_size": 1234,
  "total_pages": 124,
  "has_previous": false,
  "has_next": true,
  "data": [ { /* row */ } ]
}
```
Errors are returned as `{"error": "..."}` with status **400 / 403 / 500**.

---

## Endpoints

### 1. `POST /api/get_masterlist`
Returns players from the **MasterList** table. This is the main player search endpoint.

Filtering applied by the server before your `filter`/`cols`:
- `public_player = True` — non-public players are **never** returned (so filtering on
  `public_player=False` yields nothing).
- `state__in` the package's `can_see_states`.
- If the package **cannot** see portal/archive (`can_see_portal_and_archive = False`),
  results are restricted to `class_field` in `restricted_years`
  (`2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034`).

See the [MasterList searchable fields](#masterlist--searchable-fields) section for the full
list of fields you can put in `filter` / `cols`.

### 2. `POST /api/get_measurable`
Returns all rows from the **Measurable** table (camp/event definitions). **Not** package-filtered
by state, but still requires a valid key and a `college` field.

Fields: `dbkey`, `public`, `location`, `priority`, `state`, `date`, `type`, `leaderboard`, `modified`.

### 3. `POST /api/get_measurablecamp`
Returns **MeasurableCamp** rows (per-player camp measurables). Package-filtered through the related
player (`player_dbkey__state__in` and, unless portal/archive is allowed, `player_dbkey__class_field__in`
restricted years).

Fields: `dbkey`, `measurable_dbkey`, `player_dbkey`, `height`, `weight`, `ten`, `shoe`, `forty`,
`arm`, `broad`, `hand`, `reach`, `shuttle`, `vertical`, `wingspan`, `jersey`, `sparq`, `ldrill`, `modified`.

### 4. `POST /api/get_measurabletrack`
Returns **MeasurableTrack** rows (track & field marks). Same package filtering as camp.

Fields: `dbkey`, `measurable_dbkey`, `player_dbkey`, `track55m`(+`Date`), `track60m`(+`Date`),
`track100m`(+`Date`), `track200m`(+`Date`), `trackLJ`(+`Date`), `trackSP`(+`Date`), `tripleJump`(+`Date`),
`highJump`(+`Date`), `track110mh`(+`Date`), `discus`(+`Date`), `modified`.

### 5. `POST /api/get_measurablespeed`
Returns **MeasurableSpeed** rows (max-speed camp data). Same package filtering as camp, **plus** it
requires the package's `can_see_max_speed` permission — otherwise the server raises
`"College Cannot See Speed Camps"` and returns **500**.

Fields: `dbkey`, `measurable_dbkey`, `player_dbkey`, `max_speed`, `max_speed_date`, `max_speed_video`,
`explosiveness`, `modified`.

### 6. `POST /api/get_collegeoffers`
Returns **CollegeOffers** rows. Same package filtering as camp (via the related player).

Fields: `dbkey`, `player_dbkey`, `school_name`, `offer_date`, `conference`, `state`, `updated`, `show`.

---

## Error responses

| Status | When | Body |
|--------|------|------|
| **403** | `key` header missing or not in `valid_keys` | `{"error": "access denied"}` |
| **400** | Body has no `college` field | `{"error": "No College"}` |
| **404** | Trailing slash on the route | (Django 404) |
| **500** | Speed endpoint without `can_see_max_speed`, bad JSON, unknown college, or any other exception | `{"error": "<message>"}` |

---

## MasterList — searchable fields

Every field below can be used in `filter` (with a Django lookup) and in `cols`. Use the **field
name** in the left column, not the database column. Fields are grouped for readability; the table
maps each searchable field to its type and underlying DB column.

### Identity & name
| Field | Type | DB column |
|-------|------|-----------|
| `dbkey` | int (PK) | `Dbkey` |
| `player_id` | int (unique) | `Player id` |
| `first` | string | `First` |
| `middle_initial` | string | `Middle Initial` |
| `last` | string | `Last` |
| `nickname` | string | `Nickname` |
| `tag` | string | `tag` |

### Class / eligibility
| Field | Type | DB column |
|-------|------|-----------|
| `class_field` | int (grad year) | `Class` |
| `juco_class` | int | `juco_class` |
| `juco` | string | `Juco` |
| `years_of_eligibility` | string | — |

### Contact & location
| Field | Type | DB column |
|-------|------|-----------|
| `home_address` | string | `Home Address` |
| `city` | string | `City` |
| `state` | string (state code) | `State` |
| `zip_code` | string | `Zip` |
| `home_phone` | string | `Home Phone` |
| `cell_phone` | string | `Cell Phone` |
| `email` | string | `Email` |
| `birth_date` | string | `Birth Date` |
| `birth_state` | string (state code) | `Birth State` |
| `preferred_airport` | string | `Preferred Airport` |
| `time_zone` | string | `Time Zone` |
| `county` | string | `County` |
| `latitude` | float | — |
| `longitude` | float | — |

### High school
| Field | Type | DB column |
|-------|------|-----------|
| `ets_code` | string | `Etscode` |
| `school_name` | string | `School Name` |
| `school_address` | string | `School Address` |
| `school_city` | string | `School City` |
| `school_zip` | string | `School Zip` |
| `school_state` | string | `School State` |
| `school_phone` | string | `Main Phone` |
| `fax` | string | `Fax` |
| `gpa` | string | — |
| `head_coach` | string | `Head Coach` |
| `head_coach_cell` | string | `Head Coach Cell` |
| `head_coach_office` | string | `Head Coach Office` |
| `head_coach_email` | string | `Head Coach Email` |
| `athletic_director_name` | string | `AD Name` |
| `athletic_director_email` | string | `AD Email` |
| `athletic_director_cell` | string | `AD Cell` |
| `guidance_counselor_name` | string | `Guidance Counselor Name` |
| `guidance_counselor_phone` | string | `Guidance Counselor Phone` |
| `guidance_counselor_email` | string | `Guidance Counselor Email` |
| `recruiting_asst_coach_name` | string | `Recruiting / Asst. Coach Name` |
| `recruiting_asst_coach_cell` | string | `Recruiting / Asst. Coach Cell` |
| `recruiting_asst_coach_email` | string | `Recruiting / Asst. Coach Email` |

### JUCO school (transfer/JUCO mirror of the HS fields)
| Field | Type | DB column |
|-------|------|-----------|
| `juco_ets_code` | string | — |
| `juco_school_name` | string | — |
| `juco_school_address` | string | — |
| `juco_school_city` | string | — |
| `juco_school_zip` | string | — |
| `juco_school_state` | string | — |
| `juco_county` | string | — |
| `juco_time_zone` | string | — |
| `juco_school_phone` | string | — |
| `juco_fax` | string | — |
| `juco_gpa` | string | — |
| `juco_head_coach` | string | — |
| `juco_head_coach_cell` | string | — |
| `juco_head_coach_office` | string | — |
| `juco_head_coach_email` | string | — |
| `juco_athletic_director_name` | string | — |
| `juco_athletic_director_email` | string | — |
| `juco_athletic_director_cell` | string | — |
| `juco_guidance_counselor_name` | string | — |
| `juco_guidance_counselor_phone` | string | — |
| `juco_guidance_counselor_email` | string | — |
| `juco_recruiting_asst_coach_name` | string | — |
| `juco_recruiting_asst_coach_cell` | string | — |
| `juco_recruiting_asst_coach_email` | string | — |

### Other coaches / agents
| Field | Type | DB column |
|-------|------|-----------|
| `coach_name_7_on_7` | string | `Coach Name 7 on 7` |
| `coach_cell_7_on_7` | string | `Coach Cell 7 on 7` |
| `coach_email_7_on_7` | string | `Coach Email 7 on 7` |
| `trainer_coach_name` | string | `Trainer Coach Name` |
| `agency_name` | string | `Agency Name` |
| `agent_name` | string | `Agent Name` |
| `agent_cell` | string | `Agent Cell` |

### Family
| Field | Type | DB column |
|-------|------|-----------|
| `custodial_parent` | string | `Custodial Parent` |
| `father_name` | string | `Father Name` |
| `father_cell` | string | `Father Cell` |
| `father_email` | string | `Father Email` |
| `father_college` | string | `Father College` |
| `father_occupation` | string | `Father Occupation` |
| `father_birth_date` | date | — |
| `mother_name` | string | `Mother Name` |
| `mother_cell` | string | `Mother Cell` |
| `mother_email` | string | `Mother Email` |
| `mother_college` | string | `Mother College` |
| `mother_occupation` | string | `Mother Occupation` |
| `mother_birth_date` | date | — |
| `guardian_name` | string | `Guardian Name` |
| `guardian_cell` | string | `Guardian Cell` |
| `guardian_email` | string | `Guardian Email` |
| `parents_married_divorced` | string | `Parents Married Divorced` |
| `siblings_names` | string | `Siblings Names` |
| `siblings_colleges` | string | `Siblings Colleges` |
| `siblings_sports` | string | `Siblings Sports` |

### Position, scheme & evaluation
| Field | Type | DB column |
|-------|------|-----------|
| `position_played` | string | `Position Played` |
| `position_projected` | string | `Position Projected` |
| `projection_change` | date | `Projection Change` |
| `jersey` | int | `Jersey` |
| `high_school_scheme` | string | `High School Scheme` |
| `college_level_projection` | string | `College Level Projection` |
| `freshman_film_evaluation` | string | `Freshman Film Evaluation` |
| `freshman_film_evaluation_date` | date | — |
| `sophomore_film_evaluation` | string | `Sophomore Film Evaluation` |
| `sophomore_film_evaluation_date` | date | — |
| `camp_event_evaluation` | string | `Camp Event Evaluation` |
| `camp_event_videos` | string | `Camp Event Videos` |
| `injury_history` | string | `Injury History` |
| `notes` | string | — |
| `admin_notes` | string | `Admin Notes` |

### Recruiting status & offers
| Field | Type | DB column |
|-------|------|-----------|
| `commit` | string | — |
| `college_offers` | string | `College Offers` |
| `detailed_college_offers` | string | `Detailed College Offers` |
| `got_new_offer` | bool | — |
| `status` | string | `Status` |
| `region` | string | `Region` |
| `college_enrolled` | string | `College Enrolled` |
| `college_signed` | string | `College Signed` |
| `deleted_from_pf_roster` | string | `Deleted from PF Roster` |
| `transfer` | string | `Featured Player` |
| `featured_text` | string | `Featured Text` |
| `featured_from` | date | `Featured From` |
| `featured_to` | date | `Featured To` |

### Rankings
| Field | Type | DB column |
|-------|------|-----------|
| `espn_300_rank` | int | `ESPN 300 Rank` |
| `espn_positional_rank` | int | `ESPN Positional Rank` |
| `espn_stars` | string | `ESPN Stars` |
| `uc_score` | float | — |
| `class_score` | float | — |
| `sparq` | float | `Sparq` |

### Physical measurables (verified)
| Field | Type | DB column |
|-------|------|-----------|
| `height` | float | `Height` |
| `height_verified` | bool | — |
| `weight` | int | `Weight` |
| `weight_verified` | bool | — |
| `hand` | float | `Hand Verified` |
| `wingspan` | float | `Wingspan Verified` |
| `arm` | float | `Arm` |
| `arm_length_verified` | float | `Arm Length Verified` |
| `arm_length_verified_date` | date | `Arm Length Verified Date` |
| `arm_length_verified_location` | string | `Arm Length Verified Location` |
| `reach` | float | `Reach` |
| `broad` | float | `Broad` |
| `vertical` | float | `Vertical Verified` |
| `shuttle` | float | `Shuttle Verified` |
| `ldrill` | float | `LDrill` |
| `ten` | float | `Ten` |
| `forty` | float | `Verified 40` |

### Speed
| Field | Type | DB column |
|-------|------|-----------|
| `max_speed` | float | `Max Speed` |
| `speed_verified` | float | — |

### Track & field marks
| Field | Type | DB column |
|-------|------|-----------|
| `track55m` | float | `Track55M` |
| `track60m` | float | `Track60M` |
| `track100m` | float | `Verified 100M` |
| `track200m` | float | `Track200M` |
| `trackLJ` | float | `TrackLJ` |
| `trackSP` | float | `TrackSP` |
| `tripleJump` | float | — |
| `highJump` | float | — |
| `track110mh` | float | — |
| `discus` | float | — |
| `milesplit_url` | string | — |

### Transfer-portal stats
| Field | Type | DB column |
|-------|------|-----------|
| `completions` | float | — |
| `attempts` | float | — |
| `completion_percent` | float | — |
| `passing_yard` | float | — |
| `passing_touchdowns` | float | — |
| `interceptions` | float | — |
| `rushing_yards` | float | — |
| `rushing_touchdowns` | float | — |
| `carries` | float | — |
| `average_per_carry` | float | — |
| `receptions` | float | — |
| `receiving_touchdowns` | float | — |
| `receiving_yards` | float | — |
| `yards_per_catch` | float | — |
| `games_played` | float | — |
| `games_started` | float | — |
| `tackles` | float | — |
| `tackles_for_loss` | float | — |
| `sacks` | float | — |
| `forced_fumbles` | float | — |
| `pass_breakups` | float | — |
| `all_conference` | string | — |
| `college_position` | string | — |
| `college_height` | float | — |
| `college_weight` | float | — |
| `college_division` | string | — |
| `college_class` | string | — |
| `transfer_updated` | datetime | — |

### Media & social
| Field | Type | DB column |
|-------|------|-----------|
| `player_head_shot` | string | `Player Head Shot` |
| `front_photo` | string | `Front Photo` |
| `front_photo_2` | string | `Front Photo 2` |
| `back_photo` | string | `Back Photo` |
| `back_photo_2` | string | `Back Photo 2` |
| `assessment_photo` | string | — |
| `assessment_photo_2` | string | — |
| `preferred_image` | string | — |
| `max_speed_video` | string | — |
| `hudl_video_link` | string | `Hudl Video Link` |
| `twitter` | string | `Player Twitter` |
| `instagram` | string | `Instagram` |
| `facebook` | string | `Facebook` |
| `snapchat` | string | `Snapchat` |
| `tik_tok` | string | — |

### Personal / misc
| Field | Type | DB column |
|-------|------|-----------|
| `other_varsity_sports` | string | `Other Varsity Sports` |
| `other_sports_stats` | string | `Other Sports Stats` |
| `academic_interest` | string | `Academic Interest` |
| `awards_won` | string | `Awards Won` |
| `hobbies` | string | `Hobbies` |
| `favorite_music_artist` | string | — |
| `favorite_food_or_snack` | string | — |
| `favorite_video_game` | string | — |
| `shirt_size` | string | `Shirt Size` |
| `cleat_size` | string | `Cleat Size` |

### Scraping / external IDs / internal
| Field | Type | DB column |
|-------|------|-----------|
| `main_scrape_url` | string | — |
| `timeline_scrape_url` | string | — |
| `maxpreps_main_link` | string | — |
| `maxpreps_school_link` | string | — |
| `maxpreps_stats_link` | string | — |
| `maxpreps_inactive_page` | string | — |
| `playerfirst_id` | int | `PlayerFirstID` |
| `public_player` | bool | — (always forced to `True` on this endpoint) |
| `twoFourLocation` | string | — |
| `twoFourInsertDate` | datetime | — |
| `twoFourLocationChecked` | string | — |
| `twoFourLocationCheckedDate` | datetime | — |
| `twoFourChecked` | datetime | — |
| `created` | datetime | `Created` |
| `updated` | datetime | `Modified` |

---

## Example request

```bash
curl -X POST https://football-api-dot-football-344319.uc.r.appspot.com/api/get_masterlist \
  -H "Content-Type: application/json" \
  -H "key: YOUR_API_KEY" \
  -d '{
        "college": "Florida Atlantic",
        "page": 0,
        "limit": 10,
        "filter": { "first__icontains": "john", "class_field": 2026, "state__in": ["FL", "GA"] },
        "cols": ["first", "last", "state", "class_field", "position_played"]
      }'
```
