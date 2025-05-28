## 🛒 Shop System Documentation
This guide explains how to manage shops using the `.shop_admin` command suite.

---

### 🔧 General Usage

```bash
.shop_admin add <shop_type> <item_json>
.shop_admin remove <shop_type> <item_id>
.shop_admin list <shop_type>
.shop_admin edit <shop_type> <item_id> <field> <value>
```

---

### 🏍️ Available Shop Types

* `items`: General items
* `potions`: Buff potions
* `upgrades`: Permanent upgrades
* `bait`: Fishing bait
* `rod`: Fishing rods
* `fish`: Fish buying/selling (manual or future extension)

---

### 🍭 `items` Shop

For general items.

#### Required Fields

* `id`: Unique string identifier
* `name`: Display name
* `price`: Cost in bronkbuks
* `description`: Description

#### Possible Fields

* `amount`: Quantity given

#### Example

```bash
.shop_admin add items {"id": "vip", "name": "VIP Role", "price": 10000, "description": "Get VIP status"}
```

---

### 🧪 `potions` Shop

For buff potions.

#### Required Fields

* `id`
* `name`
* `price`
* `type`: Buff type (e.g. `"luck"`)
* `multiplier`: Effect strength (e.g. 2.0)
* `duration`: Duration in minutes

#### Optional Fields

* `description`: Custom description to override default buff description

#### Example

```bash
.shop_admin add potions {"id": "luck_potion", "name": "Lucky Potion", "price": 1000, "type": "luck", "multiplier": 2.0, "duration": 60}
```

---

### ⚡ `upgrades` Shop

For permanent upgrades.

#### Required Fields

* `id`
* `name`
* `price`
* `type`: Upgrade type (e.g. `"bank"`, `"inventory"`)
* `amount`: Upgrade effect amount

#### Example

```bash
.shop_admin add upgrades {"id": "bank_boost", "name": "Bank Boost", "price": 5000, "type": "bank", "amount": 10000}
```

---

### 🎣 Fishing Shops

There are three fishing-related shop types:

* `bait`: Bait for fishing
* `rod`: Fishing rods
* `fish`: Fish (buy/sell)

#### 🦡 Bait Shop

##### Required Fields

* `id`
* `name`
* `price`
* `amount`: Amount of bait units
* `description`
* `catch_rates`: Dict of fish types and their chances

```bash
.shop_admin add bait {"id": "mutated_bait", "name": "Mutated Bait", "price": 200, "amount": 5, "description": "Catch mutated fish", "catch_rates": {"normal": 1.5, "rare": 0.5, "event": 0.2, "mutated": 0.1}}
```

#### 🎣 Rod Shop

##### Required Fields

* `id`
* `name`
* `price`
* `description`
* `multiplier`: Catch rate multiplier

```bash
.shop_admin add rod {"id": "pro_rod", "name": "Pro Rod", "price": 5000, "description": "Better catch rate", "multiplier": 1.5}
```

---

### 📅 Editing Items

```bash
.shop_admin edit <shop_type> <item_id> <field> <value>
```

* Type conversion is automatic for: `price`, `multiplier`, `duration`, `amount`
* Set value to `"null"` to delete the field

#### Example

```bash
.shop_admin edit potions luck_potion price 2000
```

---

### ❌ Removing Items

```bash
.shop_admin remove <shop_type> <item_id>
```

#### Example

```bash
.shop_admin remove items vip
```

---

### 📋 Listing Items

```bash
.shop_admin list <shop_type>
```

#### Example

```bash
.shop_admin list rod
```

---

### 🧪 Server-Specific Potion Example

This is done using a custom internal method:

```python
await self.server_add_potion(
    ctx,
    name="Mega Luck",
    price=5000,
    type="luck",
    multiplier=3.0,
    duration=30,
    description="Grants insane luck"
)
```

---