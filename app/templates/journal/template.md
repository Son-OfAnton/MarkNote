---
title: {{ title }}
created_at: {{ created_at }}
updated_at: {{ updated_at }}
{% if tags %}tags:
{% for tag in tags %}  - {{ tag }}
{% endfor %}{% endif %}
{% if category %}category: {{ category }}{% endif %}
type: journal
date: {{ date | default(created_at.split('T')[0]) }}
mood: {{ mood | default('') }}
---

# {{ title }}

## Today's Highlights

- 
- 
- 

## Thoughts and Reflections

## Gratitude

Things I'm grateful for today:

1. 
2. 
3. 

## Tomorrow's Focus

- [ ] 
- [ ] 
- [ ]