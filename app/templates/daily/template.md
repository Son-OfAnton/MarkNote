---
title: {{ title }}
created_at: {{ created_at }}
updated_at: {{ updated_at }}
{% if tags %}tags:
{% for tag in tags %}  - {{ tag }}
{% endfor %}{% endif %}
{% if category %}category: {{ category }}
{% endif %}{% if linked_notes %}linked_notes:
{% for link in linked_notes %}  - {{ link }}
{% endfor %}{% endif %}type: daily
date: {{ date | default(created_at.split('T')[0]) }}
day_of_week: {{ day_of_week | default('') }}
---

# {{ title }}

## Tasks for Today

- [ ] 
- [ ] 
- [ ] 

## Notes & Ideas

## Daily Journal

### Morning Thoughts


### Evening Reflection


## Health & Wellness

- Sleep: 
- Exercise: 
- Mood: 

{% if linked_notes %}
## Related Notes

{% for link in linked_notes %}* [[{{ link }}]]
{% endfor %}
{% endif %}

## Tomorrow's Planning

- [ ] 
- [ ] 
- [ ]