"use client";

import { Row, Col, Form, Button, Spinner, Accordion } from "react-bootstrap";
import { useForm, useFieldArray } from "react-hook-form";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { recalculateConditional } from "../queries";
import { useStore } from "../store";

export default function ConditionalForm({ data, seerData, params, cohortIndex, fitIndex }) {
  const queryClient = useQueryClient();
  const isFetching = queryClient.isFetching();
  const intervalOptions = [...new Set(data.fullpredicted.map((e) => e.Interval))];
  const setState = useStore((state) => state.setState);
  const useConditional = useStore((state) => state.useConditional);

  const {
    control,
    register,
    watch,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm({
    defaultValues: {
      conditional: useConditional,
      conditionalIntervals: [{ start: "", end: "" }],
    },
  });
  const { fields, append, remove, update } = useFieldArray({
    control,
    name: "conditionalIntervals",
  });
  const conditional = watch("conditional");

  function handleConditionalChange(e) {
    setValue("conditional", e.target.checked);
    setState({ useConditional: e.target.checked });
  }

  async function conditionalCalculation(form) {
    try {
      const { data } = await queryClient.fetchQuery({
        queryKey: ["conditional", cohortIndex, fitIndex],
        queryFn: async () =>
          recalculateConditional(params.id, { cohortIndex, fitIndex, conditionalIntervals: form.conditionalIntervals }),
      });

      setState({ conditional: data });
    } catch (e) {
      console.log(e);
    }
  }

  return (
    <Accordion defaultActiveKey={0}>
      <Accordion.Item eventKey="0">
        <Accordion.Header>Conditional Survival Calculation</Accordion.Header>
        <Accordion.Body>
          <Form onSubmit={handleSubmit(conditionalCalculation)}>
            <p className="fw-bold">
              Support for <i>Survival vs. Year at Diagnosis</i> and <i>Survival vs. Time since Diagnosis</i> only
            </p>
            <Row>
              <Col sm="10">
                <Row>
                  <Col>
                    <Form.Group>
                      <Form.Check
                        {...register("conditional")}
                        id="conditional"
                        label="Conditional survival recalculation based on model previously fit to all intervals"
                        aria-label="conditional recalculation"
                        type="checkbox"
                        onChange={handleConditionalChange}
                      />
                    </Form.Group>
                  </Col>
                  {fields.map((field, i) => (
                    <Row key={i} className="mb-3">
                      <Col sm="auto">
                        <Form.Group className="d-flex align-items-center">
                          <Form.Label className="me-2">From</Form.Label>
                          <Form.Select
                            {...register(`conditionalIntervals[${i}].start`, {
                              valueAsNumber: true,
                              required: conditional ? "Required" : false,
                              validate: (value, form) =>
                                value < form.conditionalIntervals[i].end ||
                                `Must be less than ${+form.conditionalIntervals[i].end + yearStart}`,
                            })}
                            disabled={!conditional || isFetching}
                            isInvalid={errors?.conditionalIntervals && errors?.conditionalIntervals[i]?.start}>
                            {intervalOptions.map((value) => (
                              <option key={value} value={value}>
                                {value}
                              </option>
                            ))}
                          </Form.Select>
                          <Form.Control.Feedback type="invalid">
                            {errors?.conditionalIntervals && errors?.conditionalIntervals[i]?.start?.message}
                          </Form.Control.Feedback>
                        </Form.Group>
                      </Col>
                      <Col sm="auto">
                        <Form.Group className="d-flex align-items-center">
                          <Form.Label className="me-2">To</Form.Label>
                          <Form.Select
                            {...register(`conditionalIntervals[${i}].end`, {
                              valueAsNumber: true,
                              required: conditional ? "Required" : false,
                              validate: (value, form) =>
                                value > form.conditionalIntervals[i].start ||
                                `Must be greater than ${+form.conditionalIntervals[i].start + yearStart}`,
                            })}
                            disabled={!conditional || isFetching}
                            isInvalid={errors?.conditionalIntervals && errors?.conditionalIntervals[i]?.end?.message}>
                            {intervalOptions.map((value) => (
                              <option key={value} value={value}>
                                {value}
                              </option>
                            ))}
                          </Form.Select>
                          <Form.Control.Feedback type="invalid">
                            {errors?.conditionalIntervals && errors?.conditionalIntervals[i]?.end?.message}
                          </Form.Control.Feedback>
                        </Form.Group>
                      </Col>
                      {i === 0 ? (
                        <Col className="d-flex">
                          <Button
                            className="ml-auto"
                            disabled={!conditional}
                            variant="link"
                            onClick={() =>
                              append({
                                start: "",
                                end: "",
                              })
                            }
                            title="Add Interval"
                            style={{ textDecoration: "none" }}>
                            <span className="text-nowrap" title="Add Interval">
                              + Add Interval
                            </span>
                          </Button>
                        </Col>
                      ) : (
                        <Col md="auto" className="d-flex">
                          <Button
                            className="ml-auto"
                            disabled={!conditional}
                            variant="link"
                            onClick={() => remove(i)}
                            title={"Remove Interval " + (parseInt(i) + 1)}
                            style={{ textDecoration: "none" }}>
                            <span className="text-nowrap" title="Remove Interval">
                              - Remove Interval
                            </span>
                          </Button>
                        </Col>
                      )}
                    </Row>
                  ))}
                </Row>
              </Col>
              <Col sm="2" className="d-flex justify-content-center align-items-center">
                <Button type="submit" disabled={!conditional || isFetching}>
                  {isFetching ? (
                    <>
                      <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" /> Loading
                    </>
                  ) : (
                    "Submit"
                  )}
                </Button>
              </Col>
            </Row>
          </Form>
        </Accordion.Body>
      </Accordion.Item>
    </Accordion>
  );
}
