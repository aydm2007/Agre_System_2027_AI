[TestMethod]
public void RuntimeProbe_CriminalAudit()
{
    // Arrange
    var probe = new RuntimeProbe();

    // Act
    var result = probe.AuditCriminalCompliance();

    // Assert
    Assert.IsTrue(result);
}