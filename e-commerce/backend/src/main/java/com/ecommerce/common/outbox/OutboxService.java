package com.ecommerce.common.outbox;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;

@Service
@RequiredArgsConstructor
@Slf4j
public class OutboxService {
    private final OutboxRepository outboxRepository;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    @Transactional(propagation = Propagation.MANDATORY)
    public void publish(DomainEvent event) {
        try {
            String serializedEvent = objectMapper.writeValueAsString(event);
            OutboxEvent newEvent = new OutboxEvent(
                    event.eventId(),
                    event.aggregateType(),
                    event.aggregateId(),
                    event.eventType(),
                    serializedEvent,
                    event.schemaVersion(),
                    clock.instant()
            );
            outboxRepository.save(newEvent);
            log.debug("Outbox event persisted: type={}, aggregateId={}, eventId={}",
                    event.eventType(), event.aggregateId(), event.eventId());
        } catch (JsonProcessingException e) {
            throw new OutboxSerializationException(
                    "failed to serialize event " + event.eventType() + " for aggregate " + event.aggregateId(),
                    e
            );
        }

    }
}
