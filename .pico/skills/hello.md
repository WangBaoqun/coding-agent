---
name: hello
description: A simple greeting skill
category: demo
parameters:
  - name: name
    type: string
    required: false
    description: Name to greet
    default: World
---

# Hello Skill

Say hello to `{name}` in a friendly way.

Include a fun fact or a joke to make the greeting more interesting.

```python
print(f"Hello, {name}!")
```
