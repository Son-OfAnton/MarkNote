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
{% endfor %}{% endif %}type: meeting
---

# {{ title }}

## Meeting Details

**Date:** {{ meeting_date | default('TBD') }}
**Time:** {{ meeting_time | default('TBD') }}
**Location:** {{ location | default('TBD') }}
**Attendees:** {{ attendees | default('TBD') }}

## Agenda

1. 
2. 
3. 

## Discussion

### Topic 1

### Topic 2

### Topic 3

## Action Items

- [ ] 
- [ ] 
- [ ] 

{% if linked_notes %}
## Related Notes

{% for link in linked_notes %}* [[{{ link }}]]
{% endfor %}
{% endif %}

## Next Steps