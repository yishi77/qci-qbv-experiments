#pragma once

#include "inet/common/TagBase.h"

namespace inet {

class QciSequenceTag : public TagBase
{
  protected:
    int sequenceNumber = -1;
    bool inserted = false;
    bool reorderMode = false;

  public:
    QciSequenceTag() = default;
    QciSequenceTag(const QciSequenceTag& other) : TagBase(other), sequenceNumber(other.sequenceNumber), inserted(other.inserted), reorderMode(other.reorderMode) {}
    virtual QciSequenceTag *dup() const override { return new QciSequenceTag(*this); }
    int getSequenceNumber() const { return sequenceNumber; }
    void setSequenceNumber(int value) { sequenceNumber = value; }
    bool isInserted() const { return inserted; }
    void setInserted(bool value) { inserted = value; }
    bool isReorderMode() const { return reorderMode; }
    void setReorderMode(bool value) { reorderMode = value; }
};

} // namespace inet
