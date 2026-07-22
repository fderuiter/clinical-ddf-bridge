from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from neo4j import AsyncSession

class ItemMappingStatus(BaseModel):
    item_id: Optional[str]
    internal_id: Optional[int]
    is_mapped: bool

class ActivityReport(BaseModel):
    epoch_id: Optional[str]
    epoch_internal_id: int
    scheduled_event_id: Optional[str]
    scheduled_event_internal_id: int
    activity_def_id: Optional[str]
    activity_def_internal_id: int
    status: str  # 'complete', 'incomplete', 'unmapped'
    unmapped_items: List[ItemMappingStatus]
    mapped_items: List[ItemMappingStatus]

class StudyAlignmentReport(BaseModel):
    study_id: str
    complete_activities: List[ActivityReport]
    incomplete_activities: List[ActivityReport]
    unmapped_activities: List[ActivityReport]
    unmapped_odm_items: List[Dict[str, Any]]
    unmapped_crf_item_values: List[Dict[str, Any]]

async def get_unmapped_odm_items(session: AsyncSession) -> List[Dict[str, Any]]:
    query = """
    MATCH (odm)
    WHERE ('ODMItem' IN labels(odm) OR 'CDISCODMItem' IN labels(odm))
    AND NOT (odm)-[]->(:ActivityItem {active: true})
    RETURN id(odm) AS internal_id, odm.id AS node_id, labels(odm) AS node_labels
    """
    result = await session.run(query)
    return [
        {
            "internal_id": record["internal_id"],
            "node_id": record["node_id"],
            "node_labels": record["node_labels"]
        }
        async for record in result
    ]

async def get_unmapped_crf_item_values(session: AsyncSession) -> List[Dict[str, Any]]:
    query = """
    MATCH (crf)
    WHERE ('CRFItemValue' IN labels(crf) OR 'CRFNode' IN labels(crf) OR 'CRFItem' IN labels(crf))
    AND NOT (crf)-[]->(:ActivityDefinition)
    RETURN id(crf) AS internal_id, crf.id AS node_id, labels(crf) AS node_labels
    """
    result = await session.run(query)
    return [
        {
            "internal_id": record["internal_id"],
            "node_id": record["node_id"],
            "node_labels": record["node_labels"]
        }
        async for record in result
    ]

async def evaluate_epoch_activities(session: AsyncSession, study_id: str):
    query = """
    MATCH (s:Study)-[]->(e)-[]->(sei)-[]->(ad)
    WHERE s.id = $study_id 
      AND ('Epoch' IN labels(e) OR 'StudyEpoch' IN labels(e))
      AND ('ScheduledEventInstance' IN labels(sei) OR 'ScheduledActivity' IN labels(sei))
      AND ('ActivityDefinition' IN labels(ad) OR 'Activity' IN labels(ad))
    OPTIONAL MATCH (ad)-[]->(ai)
    WHERE 'ActivityItem' IN labels(ai) AND ai.active = true
    OPTIONAL MATCH (odm)-[]->(ai)
    WHERE ('ODMItem' IN labels(odm) OR 'CRFItem' IN labels(odm) OR 'CRFNode' IN labels(odm))
    WITH e, sei, ad, ai, odm
    RETURN id(e) AS epoch_internal_id, e.id AS epoch_id,
           id(sei) AS sei_internal_id, sei.id AS scheduled_event_id,
           id(ad) AS ad_internal_id, ad.id AS activity_def_id,
           collect(CASE WHEN ai IS NOT NULL THEN {
               item_id: ai.id,
               internal_id: id(ai),
               is_mapped: odm IS NOT NULL
           } END) AS items
    """
    result = await session.run(query, study_id=study_id)
    
    complete = []
    incomplete = []
    unmapped = []
    
    async for record in result:
        items = record["items"]
        # Filter out nulls from collect(CASE WHEN ...)
        items = [i for i in items if i is not None]
        
        mapped_items = [ItemMappingStatus(**i) for i in items if i['is_mapped']]
        unmapped_items = [ItemMappingStatus(**i) for i in items if not i['is_mapped']]
        
        status = "complete"
        if not items:
            # No activity items defined, consider it unmapped
            status = "unmapped"
        elif not mapped_items:
            status = "unmapped"
        elif unmapped_items:
            status = "incomplete"
            
        report = ActivityReport(
            epoch_id=record["epoch_id"],
            epoch_internal_id=record["epoch_internal_id"],
            scheduled_event_id=record["scheduled_event_id"],
            scheduled_event_internal_id=record["sei_internal_id"],
            activity_def_id=record["activity_def_id"],
            activity_def_internal_id=record["ad_internal_id"],
            status=status,
            unmapped_items=unmapped_items,
            mapped_items=mapped_items
        )
        
        if status == "complete":
            complete.append(report)
        elif status == "incomplete":
            incomplete.append(report)
        else:
            unmapped.append(report)
            
    return complete, incomplete, unmapped

async def generate_alignment_report(driver, study_id: str) -> StudyAlignmentReport:
    async with driver.session() as session:
        unmapped_odm = await get_unmapped_odm_items(session)
        unmapped_crf = await get_unmapped_crf_item_values(session)
        complete, incomplete, unmapped = await evaluate_epoch_activities(session, study_id)
        
        return StudyAlignmentReport(
            study_id=study_id,
            complete_activities=complete,
            incomplete_activities=incomplete,
            unmapped_activities=unmapped,
            unmapped_odm_items=unmapped_odm,
            unmapped_crf_item_values=unmapped_crf
        )
